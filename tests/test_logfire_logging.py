from logging import basicConfig

import logfire, os

logfire.configure(token=os.environ["LOGFIRE_TOKEN"])
basicConfig(handlers=[logfire.LogfireLoggingHandler()])
logfire.info('Hello, {place}!', place='World')