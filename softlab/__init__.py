"""Set up the main softlab namespace"""

import pkgutil
from softlab._version import get_version

from softlab import (
    jin, mu, shui, huo, tu
)

__path__ = pkgutil.extend_path(__path__, __name__)
__version__ = get_version()
