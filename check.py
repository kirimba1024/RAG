from utils import KNOWLEDGE_ROOT, to_posix
from mask import SECRET_PATTERNS
from rich.progress import track


EMOJI_MAP = [
    (['private key', 'pem', 'pgp', 'certificate'], '🔐'),
    (['password', 'passwd', 'pwd'], '🔑'),
    (['token', 'bearer', 'jwt'], '🎫'),
    (['api', 'key', 'secret'], '🗝️'),
    (['jdbc', 'mongodb', 'postgres', 'mysql', 'redis'], '🗄️'),
    (['aws', 'vault', 'keycloak'], '☁️'),
]


def classify_secret_type(pattern: str) -> str:
    """Определяет тип секрета по паттерну."""
    pattern_lower = pattern.lower()
    for keywords, emoji in EMOJI_MAP:
        if any(k in pattern_lower for k in keywords):
            return emoji
    return '⚠️'


def check_secrets_in_text(text: str) -> list[dict]:
    """Находит все потенциальные утечки в тексте."""
    findings = []
    for pat, _ in SECRET_PATTERNS:
        for match in pat.finditer(text):
            match_text = match.group(0)
            findings.append({
                'match': match_text if len(match_text) <= 120 else match_text[:120] + '...',
                'line': text[:match.start()].count('\n') + 1,
                'type': classify_secret_type(pat.pattern)
            })
    return findings


def main():
    """Основная функция сканирования."""
    files = [p for p in KNOWLEDGE_ROOT.rglob("*") if p.is_file()]
    all_findings = []
    
    for path in track(files, description="[cyan]Сканирование..."):
        try:
            findings = check_secrets_in_text(path.read_text(encoding="utf-8"))
            if findings:
                rel_posix = to_posix(path.relative_to(KNOWLEDGE_ROOT))
                for f in findings:
                    f['file'] = rel_posix
                all_findings.extend(findings)
        except (UnicodeDecodeError, OSError, PermissionError):
            pass
    
    print(f"\n🚨 {len(all_findings)}\n" if all_findings else f"\n✅ Секреты не найдены ({len(files)} файлов)\n")
    for f in all_findings:
        print(f"{f['file']}:{f['line']} {f['type']} {f['match']}")


if __name__ == '__main__':
    main()
