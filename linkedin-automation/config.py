# LinkedIn Search URL (modify filters as needed)
SEARCH_URL = (
    "https://www.linkedin.com/search/results/people/"
    "?keywords=underground%20ecom"
    "&origin=FACETED_SEARCH"
    "&geoUrn=%5B%22106057199%22,%22100446943%22,%22100876405%22,"
    "%22103323778%22,%22101855366%22,%22104035573%22,%22103420483%22%5D"
    "&pastCompany=%5B%2251591490%22,%227931942%22,%2269530400%22,"
    "%2275039061%22,%2271652776%22,%2212664866%22,%2264598473%22,%2219002150%22%5D"
    "&profileLanguage=%5B%22en%22%5D"
)

# Connection limits
MAX_CONNECTIONS_PER_RUN = 15

# Delays in seconds (min, max) — randomized each time
DELAY_BETWEEN_CONNECTIONS = (30, 90)
DELAY_BETWEEN_ACTIONS = (5, 15)
DELAY_AFTER_PAGINATION = (8, 20)

# Max search result pages to process
MAX_PAGES = 10

# Arc browser CDP connection
CDP_PORT = 9222
CDP_URL = f"http://localhost:{CDP_PORT}"

# Logging
LOG_FILE = "logs/connections.csv"
