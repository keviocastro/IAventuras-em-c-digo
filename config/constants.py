import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from dotenv import load_dotenv

FOUND_DOTENV = load_dotenv()

class EnvVars:
    @staticmethod
    def get_var(env_var_name: str) -> str:
        """
        Obtém uma variável de ambiente previamente carregada.

        Args:
            env_var_name: O nome da variável de ambiente.

        Returns:
            O valor da variável de ambiente.

        Raises:
            ValueError: Se a variável de ambiente não for encontrada.
        """
        value = os.getenv(env_var_name)
        if value is None: 
            raise ValueError(f'This environment variable "{env_var_name}" was not found. '
                             'Verify your .env.')
        return value
        
if __name__ == "__main__":
    EnvVars()