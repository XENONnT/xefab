from fabric.tasks import task
from rich.panel import Panel

from xefab.utils import console

UCHICAGO_SPLASH_SCREEN = r"""
 __   __ ______  _   _   ____   _   _      _______ 
 \ \ / /|  ____|| \ | | / __ \ | \ | |    |__   __|
  \ V / | |__   |  \| || |  | ||  \| | _ __  | |   
   > <  |  __|  | . ` || |  | || . ` || '_ \ | |   
  / . \ | |____ | |\  || |__| || |\  || | | || |   
 /_/ \_\|______||_| \_| \____/ |_| \_||_| |_||_|   

                    The UChicago Analysis Center

"""

OSG_SPLASH_SCREEN = r"""
     OOOOOOOOO        SSSSSSSSSSSSSSS         GGGGGGGGGGGGG
   OO:::::::::OO    SS:::::::::::::::S     GGG::::::::::::G
 OO:::::::::::::OO S:::::SSSSSS::::::S   GG:::::::::::::::G
O:::::::OOO:::::::OS:::::S     SSSSSSS  G:::::GGGGGGGG::::G
O::::::O   O::::::OS:::::S             G:::::G       GGGGGG
O:::::O     O:::::OS:::::S            G:::::G              
O:::::O     O:::::O S::::SSSS         G:::::G              
O:::::O     O:::::O  SS::::::SSSSS    G:::::G    GGGGGGGGGG
O:::::O     O:::::O    SSS::::::::SS  G:::::G    G::::::::G
O:::::O     O:::::O       SSSSSS::::S G:::::G    GGGGG::::G
O:::::O     O:::::O            S:::::SG:::::G        G::::G
O::::::O   O::::::O            S:::::S G:::::G       G::::G
O:::::::OOO:::::::OSSSSSSS     S:::::S  G:::::GGGGGGGG::::G
 OO:::::::::::::OO S::::::SSSSSS:::::S   GG:::::::::::::::G
   OO:::::::::OO   S:::::::::::::::SS      GGG::::::GGG:::G
     OOOOOOOOO      SSSSSSSSSSSSSSS           GGGGGG   GGGG

-----------------------------------------------------------
                              Open Science Grid: CIထ nnect
                                                           
"""

SPLASH_SCREENS = {
    "uchicago": UCHICAGO_SPLASH_SCREEN,
    "osg": OSG_SPLASH_SCREEN,
    "dali": UCHICAGO_SPLASH_SCREEN,
    "midway": UCHICAGO_SPLASH_SCREEN,
    "dali-login2.rcc.uchicago.edu": UCHICAGO_SPLASH_SCREEN,
    "dali-login1.rcc.uchicago.edu": UCHICAGO_SPLASH_SCREEN,
    "login.xenon.ci-connect.net": OSG_SPLASH_SCREEN,
    "midway2.rcc.uchicago.edu": UCHICAGO_SPLASH_SCREEN,
    "midway2-login1.rcc.uchicago.edu": UCHICAGO_SPLASH_SCREEN,
    "midway2-login2.rcc.uchicago.edu": UCHICAGO_SPLASH_SCREEN,
}


@task
def print_splash(c):
    """Print the splash screen."""

    if hasattr(c, "host"):
        if c.host in SPLASH_SCREENS:
            console.print(Panel.fit(SPLASH_SCREENS[c.host], title="Welcome"))
            return
    hostnames = getattr(c, "hostnames", [])
    if isinstance(hostnames, str):
        hostnames = hostnames.split(",")
    for host in hostnames:
        if host in SPLASH_SCREENS:
            console.print(Panel.fit(SPLASH_SCREENS[host], title="Welcome"))
            break
