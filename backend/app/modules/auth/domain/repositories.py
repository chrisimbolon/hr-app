from abc import ABC, abstractmethod


class AuthRepository(ABC):

    @abstractmethod
    def create_user(self, user, credential, tenant_id):
        pass

    @abstractmethod
    def get_user_by_email(self, email):
        pass

    @abstractmethod
    def get_user_credentials(self, user_id):
        pass

    @abstractmethod
    def increment_token_version(self, user_id):
        pass