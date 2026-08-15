"""Keep unit tests independent from deployed AWS credentials."""

import os

os.environ["FYERS_SECRET_ID"] = ""
