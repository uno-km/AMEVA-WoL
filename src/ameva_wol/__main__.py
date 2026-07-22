"""Main entrypoint module for AMEVA-WoL when executed via `python -m ameva_wol`."""

import sys
from ameva_wol.cli import main

if __name__ == "__main__":
    sys.exit(main())
