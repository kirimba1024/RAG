# frozen_string_literal: true

require 'securerandom'
require 'date'

module RAG
  module UserService
    # User represents a user in the system
    class User
      attr_reader :id, :name, :age, :email, :created_at

      def initialize(name:, age:, email: nil)
        @id = SecureRandom.uuid
        @name = name
        @age = age
        @email = email
        @created_at = DateTime.now
      end

      def to_s
        "User(id=#{id}, name=#{name}, age=#{age})"
      end

      def valid?
        name && !name.empty? && age > 0
      end
    end

    # UserService manages users
    class UserService
      def initialize(db_url)
        @db_url = db_url
        @users = []
      end

      def create_user(name:, age:, email: nil)
        user = User.new(name: name, age: age, email: email)
        @users << user
        user
      end

      def get_user(user_id)
        @users.find { |u| u.id == user_id }
      end

      def all_users
        @users.dup
      end

      def user_count
        @users.size
      end
    end
  end
end
