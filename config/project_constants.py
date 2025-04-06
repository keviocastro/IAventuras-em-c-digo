import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import datetime
from dateutil.relativedelta import relativedelta
import pytz
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

class DatetimeFormats:
    @staticmethod
    def get_datetime() -> str:
        local_time_zone = pytz.timezone("America/Sao_Paulo")
        with_timezone = datetime.datetime.now(local_time_zone)
        timestamp_postgre = with_timezone.strftime('%Y-%m-%d %H:%M:%S%z')

        return timestamp_postgre
    
    @staticmethod
    def get_datetime_plus_1_month() -> str:
        local_time_zone = pytz.timezone("America/Sao_Paulo")
        with_timezone = datetime.datetime.now(local_time_zone)
        plus_one_month = with_timezone + relativedelta(months=1)
        timestamp_postgre = plus_one_month.strftime('%Y-%m-%d %H:%M:%S%z')
        return timestamp_postgre

    @staticmethod
    def get_datetime_plus_6_months() -> str:
        local_time_zone = pytz.timezone("America/Sao_Paulo")
        with_timezone = datetime.datetime.now(local_time_zone)
        plus_six_months = with_timezone + relativedelta(months=6)
        timestamp_postgre = plus_six_months.strftime('%Y-%m-%d %H:%M:%S%z')
        return timestamp_postgre
        
if __name__ == "__main__":
    EnvVars()