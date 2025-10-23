# CLAUDE.md

## Project Overview

This is a static website that provides an alternative interface for browsing Dawncaster game data through the Blightbane API. The site consists of two main pages:

- `cards.html` - Browse and filter game cards, alternate interface for https://blightbane.io/cards
- `talents.html` - Browse and filter talent information, alternate interface for https://blightbane.io/talents

Both pages are standalone HTML files with embedded CSS and JavaScript. There is no build process, package manager, or dependencies beyond DOMPurify loaded from CDN.

## Architecture

### API Integration

All data comes from the Blightbane API at `https://blightbane.io/api`:

- **Card listing**: `GET /api/cards?search=&rarity=&category=&type=&banner=&exp=`
- **Card details**: `GET /api/card/{id}`
- **Talent details**: `GET /api/card/{id}?talent=true`

### Caching Pattern

Both pages implement client-side caching using JavaScript `Map` objects:

- Cards are cached in `cardCache` to avoid redundant API calls
- Talents are cached in `talentCache` similarly
- The cache persists for the duration of the page session

### Functional Programming Style

The code follows a functional approach with:

- Pure render functions that map data to HTML strings
- Separate functions for data fetching and DOM updates
- Immutable data transformations using `map`, `filter`, and `join`

### Data Flow

1. User selects filter options
2. `fetchCards()` or `fetchTalents()` makes API call with filter parameters
3. For each item in the results, detailed info is fetched (with caching)
4. Data is transformed and passed to render functions
5. DOM is updated with new table rows

## Development

### Running Locally

Open `cards.html` or `talents.html` directly in a web browser. No server required.

### Testing Changes

Simply refresh the browser after editing the HTML files. Browser DevTools console will show any JavaScript errors or API failures.

### Security

DOMPurify is used to sanitize all user-generated content from the API before rendering to prevent XSS attacks. The `ALLOWED_TAGS: []` configuration strips all HTML tags from descriptions.
