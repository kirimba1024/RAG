from pathlib import Path
import re
import shutil
import tempfile
from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings
from utils import clean_text, extract_binary_content, setup_logging, REPOS_ROOT, REPOS_SAFE_ROOT, is_ignored, to_posix

logger = setup_logging(Path(__file__).stem, file=False)

IGNORE_EXACT: tuple[str, ...] = (
    "SAMPLE_TOKEN_123456",
    "SAMPLE_PASSWORD_321",
    "SAMPLE_PASSWORD_444",
)

SECRET_KEYS = (
    r"(?:password|passwd|pwd|secret|token|bearer_token|api[_-]?key|x[-_]?api[-_]?key|"
    r"access[_-]?key|private[_-]?key|client[_-]?secret|refresh[_-]?token|jwt[_-]?secret|"
    r"auth[_-]?token|x[-_]?vault[-_]?token|keycloak[_-]?admin[_-]?password|"
    r"keystorePassword|truststorePassword)"
)

SECRET_PATTERNS = [
    # Порядок: специфичные паттерны → универсальные. Используем \b и лимиты длины.
    
    # PEM/PKI
    (re.compile(r"-----BEGIN ENCRYPTED PRIVATE KEY-----.*?-----END ENCRYPTED PRIVATE KEY-----", re.S), "[ENCRYPTED PRIVATE KEY REDACTED]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[PRIVATE KEY REDACTED]"),
    (re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S), "[CERTIFICATE REDACTED]"),
    (re.compile(r"-----BEGIN PGP PRIVATE KEY BLOCK-----.*?-----END PGP PRIVATE KEY BLOCK-----", re.S), "[PGP PRIVATE KEY REDACTED]"),

    # Специфичные токены
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWS ACCESS KEY REDACTED]"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,64}\b", re.I), "[GITLAB PAT REDACTED]"),
    (re.compile(r"\b(hvs\.[A-Za-z0-9]{20,256}|s\.[A-Za-z0-9]{20,256})\b"), "[VAULT TOKEN REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{20,2048}\.[A-Za-z0-9_-]{20,2048}\.[A-Za-z0-9_-]{20,2048}\b"), "[JWT REDACTED]"),

    # HTTP заголовки
    (re.compile(r"(?i)Authorization:\s*Bearer\s+[A-Za-z0-9\-\._~\+\/=]{8,512}", re.M), "Authorization: Bearer [REDACTED]"),
    (re.compile(r"(?i)Authorization:\s*Basic\s+[A-Za-z0-9+/=]{8,512}", re.M), "Authorization: Basic [REDACTED]"),
    (re.compile(r"(?i)(X[-_](?:API[-_]Key|JFrog[-_]Art[-_]Api|Vault[-_]Token)):\s*[^\s]{1,256}", re.M), r"\1: [REDACTED]"),

    # JDBC
    (re.compile(r"(?i)(jdbc:[a-z0-9:]+//[^\s]+?[?&;]password=)([^&;\s]{1,256})"), r"\1[REDACTED]"),

    # URI credentials
    (re.compile(r'(\b[a-z][a-z0-9+\-.]*://)([^:@\s]{1,256}):([^@/\s]{1,256})@', re.I), r'\1\2:[REDACTED]@'),
    (re.compile(r'(?i)([?&](?:password|pwd|pass|tlsCertificateKeyFilePassword|sslpassword|client_key_password)=)([^&#;\s]{1,256})'), r'\1[REDACTED]'),
    (re.compile(r'(?i)([;,\s])((?:password|pwd|pass)\s*=\s*)([^;,\s]{1,256})(?=[;,\s]|$)'), r'\1\2[REDACTED]'),

    # Пары ключ=значение (YAML/JSON/properties)
    (re.compile(rf"(?i)\b({SECRET_KEYS})(\s*[:=]\s*)([^\s'\"\\]{{4,256}})"), lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]"),
    (re.compile(rf'''(?i)\b({SECRET_KEYS})\s*:\s*(['"])[^'"\\]{{4,256}}\2'''), r"\1: \2[REDACTED]\2"),
    (re.compile(rf'(?i)"({SECRET_KEYS})"\s*:\s*"[^"\\]{{4,256}}"'), r'"\1": "[REDACTED]"'),

    # Конфигурационные ключи
    (re.compile(
        r"(?im)^\s*(spring\.datasource\.(?:password|hikari\.password)|flyway\.password|liquibase\.password|"
        r"spring\.mail\.password|keycloak\.(?:credentials\.secret|password)|(?:vertica|clickhouse)\.password)(\s*[:=]\s*).+$"
    ), lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]"),

    # Environment variables
    (re.compile(
        r"(?i)\b(VAULT[_-]?TOKEN|CI[_-]JOB[_-]TOKEN|JFROG_(?:ACCESS_TOKEN|API_KEY)|ARTIFACTORY_API_KEY|"
        r"KEYCLOAK_ADMIN_PASSWORD|KC_DB_PASSWORD|KC_HTTPS_PASSWORD|(?:SMTP|MAIL)[_-]?PASSWORD)(\s*[:=]\s*)[^\s]{1,256}"
    ), lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]"),

    # Vault secrets
    (re.compile(r"(?i)\b(role_id|secret_id)(\s*[:=]\s*)[0-9a-f\-]{16,256}"), lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]"),
    (re.compile(r"(?i)\b(registration[_-]?token)(\s*[:=]\s*)[A-Za-z0-9\-_]{8,256}\b"), lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]"),
    (re.compile(r"(?i)\b(aws[_-]?secret[_-]?access[_-]?key)(\s*[:=]\s*)[A-Za-z0-9/+=]{30,256}"), lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]"),

    # curl -u
    (re.compile(r"(?i)(-u\s+)([^:\s]{1,64}):([^\s]{1,256})"), r"\1\2:[REDACTED]"),

    # Kubernetes
    (re.compile(r"(?im)^\s*(token|client-key-data|client-certificate-data|certificate-authority-data)\s*:\s*[A-Za-z0-9+/=\n]{40,8192}\s*$"), 
                lambda m: re.sub(r':\s*[A-Za-z0-9+/=\n]+\s*$', ': [REDACTED]', m.group(0))),
    (re.compile(r"\bkind:\s*Secret\b.*?\b(?:data|stringData):\s*\{[^}]*\}", re.I | re.S), 
                lambda m: re.sub(r':\s*[^,\}\s]+', ': [REDACTED]', m.group(0))),
    (re.compile(r'(?i)"(?:auth|secret)"\s*:\s*"[A-Za-z0-9._\-]{16,256}"'), 
                lambda m: re.sub(r':\s*"[^"]+"', ': "[REDACTED]"', m.group(0))),

    # Maven/Gradle XML
    (re.compile(r"(?is)<(password|passphrase)>[^<]{1,1024}</\1>"), lambda m: f"<{m.group(1)}>[REDACTED]</{m.group(1)}>"),
    (re.compile(rf'(?i)\b({SECRET_KEYS})\s*=\s*"[^"{{}}]{{1,256}}"'), lambda m: re.sub(r'="[^"]+"', '="[REDACTED]"', m.group(0))),
    (re.compile(rf"(?i)\b({SECRET_KEYS})\s*=\s*'[^'{{}}]{{1,256}}'"), lambda m: re.sub(r"='[^']+'", "='[REDACTED]'", m.group(0))),
    (re.compile(r"(?im)^(artifactory_password|systemProp\.(?:http|https)\.proxyPassword)(\s*=\s*).+$"), 
                lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]"),

    # Точные строки
    *([(re.compile("|".join(map(re.escape, sorted(IGNORE_EXACT, key=len, reverse=True)))), "[REDACTED]")] if IGNORE_EXACT else []),
]

def check_secrets_in_text(text: str, file_path: str = None) -> None:
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8") as tmp:
        tmp.write(text)
        tmp_path = tmp.name
    try:
        secrets_collection = SecretsCollection()
        with default_settings():
            secrets_collection.scan_file(tmp_path)
        results_dict = secrets_collection.json()
        file_results = (results_dict.get("results") or {}).get(tmp_path, [])
        for hit in file_results:
            logger.warning(f"⚠️ {file_path} секрет: {hit.get('type', 'Unknown')} в строке {hit.get('line_number', 0)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def mask_secrets(text: str) -> str:
    for pat, repl in SECRET_PATTERNS:
        for m in pat.finditer(text):
            original = m.group(0)
            replaced = repl if isinstance(repl, str) else repl(m)
            logger.info(f"🔒 Найдено: {original} -> {replaced}")
        text = pat.sub(repl, text)
    return text


def mask_directory(src_dir: Path, dst_dir: Path):
    for item in (f for f in src_dir.rglob('**/*') if f.is_file()):
        rel_path = to_posix(item.relative_to(src_dir))
        if is_ignored(rel_path):
            continue
        dst_path = dst_dir / item.relative_to(src_dir)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = item.read_text(encoding='utf-8')
            content = mask_secrets(content)
            check_secrets_in_text(content, rel_path)
            dst_path.write_text(content, encoding='utf-8')
            logger.debug(f"Маскирован: {rel_path}")
        except UnicodeDecodeError:
            try:
                content = extract_binary_content(item)
                content = clean_text(content)
                content = mask_secrets(content)
                check_secrets_in_text(content, rel_path)
                dst_path.write_text(content, encoding='utf-8')
                logger.debug(f"Бинарный файл распознан и маскирован: {rel_path}")
            except Exception as e:
                logger.error(f"Ошибка при обработке бинарного файла {rel_path}: {e}")
                shutil.copy2(item, dst_path)
        except Exception as e:
            logger.error(f"Ошибка при обработке файла {rel_path}: {e}")
            shutil.copy2(item, dst_path)

def main():
    if REPOS_SAFE_ROOT.exists():
        shutil.rmtree(REPOS_SAFE_ROOT)
    REPOS_SAFE_ROOT.mkdir()
    mask_directory(REPOS_ROOT, REPOS_SAFE_ROOT)
    logger.info(f"Маскирование завершено: {REPOS_SAFE_ROOT}")

if __name__ == "__main__":
    main()