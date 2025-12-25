# Vulture whitelist - false positives for unused code detection
# These are parameters or functions that appear unused but are required

# Pydantic BaseSettings override - parameters required by method signature
env_settings  # noqa
dotenv_settings  # noqa

# ThreadStore.get_thread_store - used indirectly by other store functions
# and tested via test_get_thread_store
get_thread_store  # noqa
