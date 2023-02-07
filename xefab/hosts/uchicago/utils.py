from xefab.utils import console
from rich.panel import Panel
from fabric.tasks import task


SPLASH_SCREEN = r"""
 __   __ ______  _   _   ____   _   _      _______ 
 \ \ / /|  ____|| \ | | / __ \ | \ | |    |__   __|
  \ V / | |__   |  \| || |  | ||  \| | _ __  | |   
   > <  |  __|  | . ` || |  | || . ` || '_ \ | |   
  / . \ | |____ | |\  || |__| || |\  || | | || |   
 /_/ \_\|______||_| \_| \____/ |_| \_||_| |_||_|   

                    The UChicago Analysis Center

"""

@task
def print_splash(c):
    """Print the splash screen."""

    console.print(Panel.fit(SPLASH_SCREEN, title='Welcome'))

