#!/usr/bin/env python3
"""
Build Dawncaster cards database from Blightbane API.

Usage: uv run create-db/run.py <output_database.db>
"""

import sqlite3
import sys
import time
import re
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
import json


def get_bundle_version():
    """Get the current bundle version from Blightbane homepage."""
    print("Fetching bundle version from Blightbane...")
    with urlopen('https://blightbane.io') as response:
        html = response.read().decode('utf-8')

    # Extract bundle version: index.bundle.js?v=X.X.X
    match = re.search(r'index\.bundle\.js\?v=([0-9.]+)', html)
    if not match:
        raise Exception("Could not find bundle version in Blightbane homepage")

    version = match.group(1)
    print(f"  Found bundle version: {version}")
    return version


def extract_filter_array(bundle_js, pattern, filter_name):
    """Extract a filter array from the JavaScript bundle."""
    match = re.search(pattern, bundle_js)
    if not match:
        raise Exception(f"Could not find {filter_name} array in bundle")

    # The match is a JSON-like array string, parse it
    array_str = match.group(0)
    # Parse as JSON
    values = json.loads('[' + array_str + ']')
    return values


def sanitize_html(html):
    """Remove all HTML tags except <br> and <br/>."""
    if not html:
        return ''
    # Remove all tags except br
    cleaned = re.sub(r'<(?!br\s*\/?>).*?>', '', html, flags=re.IGNORECASE | re.DOTALL)
    return cleaned


def fetch_with_retry(url, max_retries=3, base_delay=1.0):
    """Fetch URL with exponential backoff retry for transient errors."""
    for attempt in range(max_retries):
        try:
            with urlopen(url) as response:
                return response.read().decode('utf-8')
        except HTTPError as e:
            # Retry on server errors (502, 503, 504)
            if e.code in (502, 503, 504):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"  HTTP {e.code} error, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    print(f"  HTTP {e.code} error, max retries exceeded")
            raise
        except URLError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"  Network error ({e.reason}), retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            raise
    raise Exception("Max retries exceeded")


def fetch_filter_data_from_bundle():
    """Fetch all filter data from Blightbane JavaScript bundle."""
    # Get bundle version
    version = get_bundle_version()

    # Fetch bundle
    bundle_url = f"https://blightbane.io/js/index.bundle.js?v={version}"
    print(f"Fetching bundle from {bundle_url}...")
    with urlopen(bundle_url) as response:
        bundle_js = response.read().decode('utf-8')

    print("Extracting filter arrays from bundle...")

    # Extract each filter array using patterns from the skill
    filters = {}

    # Categories: ["Action","Item",...]
    filters['categories'] = extract_filter_array(
        bundle_js,
        r'"Action","Item"[^]]*',
        'categories'
    )

    # Types: ["Melee","Magic",...]
    filters['types'] = extract_filter_array(
        bundle_js,
        r'"Melee","Magic"[^]]*',
        'types'
    )

    # Rarities: ["Common","Uncommon",...]
    filters['rarities'] = extract_filter_array(
        bundle_js,
        r'"Common","Uncommon"[^]]*',
        'rarities'
    )

    # Banners/Colors: ["Green","Blue","Red","Purple",...]
    filters['colors'] = extract_filter_array(
        bundle_js,
        r'"Green","Blue","Red","Purple"[^]]*',
        'colors'
    )

    # Expansions: ["Core","Metaprogress",...]
    filters['expansions'] = extract_filter_array(
        bundle_js,
        r'"Core","Metaprogress"[^]]*',
        'expansions'
    )

    return filters


def create_database(db_path):
    """Create fresh database with schema."""
    print(f"Creating database: {db_path}")

    conn = sqlite3.connect(db_path)

    # PRAGMA must be set per-connection, before other operations
    conn.execute("PRAGMA foreign_keys = ON")

    # Use executescript to run all SQL statements in one call
    conn.executescript("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        ) STRICT;

        CREATE TABLE types (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        ) STRICT;

        CREATE TABLE rarities (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        ) STRICT;

        CREATE TABLE expansions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        ) STRICT;

        CREATE TABLE colors (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        ) STRICT;

        CREATE TABLE cards (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category INTEGER NOT NULL,
            type INTEGER NOT NULL,
            rarity INTEGER NOT NULL,
            expansion INTEGER NOT NULL,
            color INTEGER NOT NULL,
            description_html TEXT NOT NULL,
            FOREIGN KEY (category) REFERENCES categories(id),
            FOREIGN KEY (type) REFERENCES types(id),
            FOREIGN KEY (rarity) REFERENCES rarities(id),
            FOREIGN KEY (expansion) REFERENCES expansions(id),
            FOREIGN KEY (color) REFERENCES colors(id)
        ) STRICT;

        CREATE INDEX idx_cards_category ON cards(category);
        CREATE INDEX idx_cards_type ON cards(type);
        CREATE INDEX idx_cards_rarity ON cards(rarity);
        CREATE INDEX idx_cards_expansion ON cards(expansion);
        CREATE INDEX idx_cards_color ON cards(color);

        CREATE TABLE costs (
            card_id INTEGER PRIMARY KEY,
            dex INTEGER NOT NULL DEFAULT 0,
            int INTEGER NOT NULL DEFAULT 0,
            str INTEGER NOT NULL DEFAULT 0,
            holy INTEGER NOT NULL DEFAULT 0,
            neutral INTEGER NOT NULL DEFAULT 0,
            dexint INTEGER NOT NULL DEFAULT 0,
            dexstr INTEGER NOT NULL DEFAULT 0,
            intstr INTEGER NOT NULL DEFAULT 0,
            blood INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (card_id) REFERENCES cards(id)
        ) STRICT;

        CREATE TABLE talents (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            tier INTEGER NOT NULL,
            expansion INTEGER NOT NULL,
            description_html TEXT NOT NULL,
            FOREIGN KEY (expansion) REFERENCES expansions(id)
        ) STRICT;

        CREATE INDEX idx_talents_tier ON talents(tier);
        CREATE INDEX idx_talents_expansion ON talents(expansion);

        CREATE TABLE talent_prerequisites (
            talent_id INTEGER NOT NULL,
            prerequisite_id INTEGER NOT NULL,
            PRIMARY KEY (talent_id, prerequisite_id),
            FOREIGN KEY (talent_id) REFERENCES talents(id),
            FOREIGN KEY (prerequisite_id) REFERENCES talents(id)
        ) STRICT;

        CREATE INDEX idx_talent_prereq_talent ON talent_prerequisites(talent_id);
        CREATE INDEX idx_talent_prereq_prerequisite ON talent_prerequisites(prerequisite_id);
    """)

    return conn


def populate_lookup_tables(conn):
    """Populate lookup tables from Blightbane bundle."""
    print("\nPopulating lookup tables...")

    # Fetch all filter data from bundle
    filters = fetch_filter_data_from_bundle()

    # Process each filter type
    # Note: Array index = filter ID in API
    for table_name, array_key, prepend_none in [
        ('categories', 'categories', False),
        ('types', 'types', False),
        ('rarities', 'rarities', False),
        ('colors', 'colors', True),      # Banner 0 = "None"
        ('expansions', 'expansions', True)  # Expansion 0 = "None"
    ]:
        values = filters[array_key]

        # Prepend "None" for colors and expansions (API uses 0 for None)
        if prepend_none:
            values = ['None'] + values

        # Skip type=8 if it's an empty string
        if array_key == 'types':
            # Remove empty string at index 8 if it exists
            values = [v for i, v in enumerate(values) if not (i == 8 and v == '')]

        print(f"  {table_name}: {len(values)} entries")

        for id_val, name in enumerate(values):
            conn.execute(
                f"INSERT INTO {table_name} (id, name) VALUES (?, ?)",
                (id_val, name)
            )

    conn.commit()


def collect_card_ids(conn):
    """Collect all unique card IDs by querying all rarity/color combinations."""
    print("\nCollecting card IDs from all rarity/color combinations...")

    # Get all rarities and colors from database
    rarities = [row[0] for row in conn.execute("SELECT id FROM rarities ORDER BY id")]
    colors = [row[0] for row in conn.execute("SELECT id FROM colors ORDER BY id")]

    total_queries = len(rarities) * len(colors)
    print(f"  Will query {len(rarities)} rarities × {len(colors)} colors = {total_queries} combinations")

    card_ids = set()
    query_count = 0

    for rarity in rarities:
        for color in colors:
            query_count += 1
            params = {
                'search': '',
                'rarity': rarity,
                'category': '',
                'type': '',
                'banner': color,
                'exp': ''
            }
            url = f"https://blightbane.io/api/cards?{urlencode(params)}"

            try:
                with urlopen(url) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    cards = data.get('cards', [])
                    for card in cards:
                        card_ids.add(card['id'])

                    if cards:  # Only print if cards were found
                        print(f"  [{query_count}/{total_queries}] Rarity {rarity}, Color {color}: {len(cards)} cards")
            except Exception as e:
                print(f"  ERROR querying rarity={rarity}, color={color}: {e}")

    print(f"\nFound {len(card_ids)} unique cards total")
    return sorted(card_ids)


def collect_talent_ids(conn):
    """Collect all unique talent IDs by querying all tier/expansion combinations."""
    print("\nCollecting talent IDs from all tier/expansion combinations...")

    # Get all expansions from database
    expansions = [row[0] for row in conn.execute("SELECT id FROM expansions ORDER BY id")]

    # Tiers are 0-6 (hardcoded as they don't change)
    tiers = list(range(7))  # 0, 1, 2, 3, 4, 5, 6

    total_queries = len(tiers) * len(expansions)
    print(f"  Will query {len(tiers)} tiers × {len(expansions)} expansions = {total_queries} combinations")

    talent_ids = set()
    query_count = 0

    for tier in tiers:
        for expansion in expansions:
            query_count += 1
            # Talents use category=10, rarity parameter maps to tier
            params = {
                'search': '',
                'rarity': tier,
                'category': 10,
                'type': '',
                'banner': '',
                'exp': expansion
            }
            url = f"https://blightbane.io/api/cards?{urlencode(params)}"

            try:
                with urlopen(url) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    talents = data.get('cards', [])
                    for talent in talents:
                        talent_ids.add(talent['id'])

                    if talents:  # Only print if talents were found
                        print(f"  [{query_count}/{total_queries}] Tier {tier}, Expansion {expansion}: {len(talents)} talents")
            except Exception as e:
                print(f"  ERROR querying tier={tier}, expansion={expansion}: {e}")

    print(f"\nFound {len(talent_ids)} unique talents total")
    return sorted(talent_ids)


def fetch_and_store_talent(conn, talent_id, index, total):
    """Fetch individual talent details and store in database (without prerequisites)."""
    url = f"https://blightbane.io/api/card/{talent_id}?talent=true"

    try:
        response_text = fetch_with_retry(url)
        talent = json.loads(response_text)

        # Sanitize description
        description = sanitize_html(talent.get('description', ''))

        # Insert talent (without prerequisites for now)
        conn.execute("""
            INSERT INTO talents (id, name, tier, expansion, description_html)
            VALUES (?, ?, ?, ?, ?)
        """, (
            talent['id'],
            talent['name'],
            talent['tier'],
            talent['expansion'],
            description
        ))

        if (index + 1) % 10 == 0 or (index + 1) == total:
            print(f"  Progress: {index + 1}/{total} talents")

        # Return prerequisites for later insertion
        return (True, talent.get('prereq', []))

    except Exception as e:
        print(f"  ERROR fetching talent {talent_id}: {e}")
        return (False, [])


def fetch_and_store_card(conn, card_id, index, total):
    """Fetch individual card details and store in database."""
    url = f"https://blightbane.io/api/card/{card_id}"

    try:
        response_text = fetch_with_retry(url)
        card = json.loads(response_text)

        # Sanitize description
        description = sanitize_html(card.get('description', ''))

        # Insert card
        conn.execute("""
            INSERT INTO cards (id, name, category, type, rarity, expansion, color, description_html)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card['id'],
            card['name'],
            card['category'],
            card['type'],
            card['rarity'],
            card['expansion'],
            card['color'],
            description
        ))

        # Insert costs
        cost = card.get('cost', {})
        conn.execute("""
            INSERT INTO costs (card_id, dex, int, str, holy, neutral, dexint, dexstr, intstr, blood)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card['id'],
            cost.get('dex', 0),
            cost.get('int', 0),
            cost.get('str', 0),
            cost.get('holy', 0),
            cost.get('neutral', 0),
            cost.get('dexint', 0),
            cost.get('dexstr', 0),
            cost.get('intstr', 0),
            cost.get('blood', 0)
        ))

        if (index + 1) % 10 == 0 or (index + 1) == total:
            print(f"  Progress: {index + 1}/{total} cards")

        return True

    except Exception as e:
        print(f"  ERROR fetching card {card_id}: {e}")
        return False


def prune_unused_filters(conn):
    """Remove filter values that do not correspond to any cards."""
    print("\nPruning unused filter values...")

    removed_any = False
    for table_name, column_name in (
        ("types", "type"),
        ("rarities", "rarity"),
        ("colors", "color"),
    ):
        removed_count = 0
        rows = list(
            conn.execute(
                f"""
                SELECT
                    lookup.id,
                    lookup.name,
                    COUNT(cards.id) AS card_count
                FROM {table_name} AS lookup
                LEFT JOIN cards ON cards.{column_name} = lookup.id
                GROUP BY lookup.id, lookup.name
                ORDER BY lookup.id
                """
            )
        )

        unused_ids = [identifier for identifier, _, count in rows if count == 0]

        if unused_ids:
            conn.executemany(
                f"DELETE FROM {table_name} WHERE id = ?",
                ((identifier,) for identifier in unused_ids),
            )
            removed_count = len(unused_ids)

        if removed_count:
            removed_any = True
            print(
                f"  Removed {removed_count} {table_name} entries with no associated cards",
                flush=True,
            )
        else:
            print(
                f"  All {table_name} values are used by at least one card",
                flush=True,
            )

    if not removed_any:
        print("  No unused filter values found")

    conn.commit()


def main():
    if len(sys.argv) != 2:
        print("Usage: uv run create-db/run.py <output_database.db>")
        sys.exit(1)

    db_path = sys.argv[1]

    print("="*60)
    print("Dawncaster Cards Database Builder")
    print("="*60)

    # Create database
    conn = create_database(db_path)

    # Populate lookup tables
    populate_lookup_tables(conn)

    # Collect and fetch talents FIRST
    talent_ids = collect_talent_ids(conn)

    print(f"\nFetching talent details (0.25s delay between requests)...")
    talent_success_count = 0
    talent_prerequisites = {}  # Store prerequisites for second pass

    for i, talent_id in enumerate(talent_ids):
        success, prereqs = fetch_and_store_talent(conn, talent_id, i, len(talent_ids))
        if success:
            talent_success_count += 1
            if prereqs:
                talent_prerequisites[talent_id] = prereqs
        time.sleep(0.25)  # Rate limiting
        conn.commit()  # Commit after each talent

    # Second pass: Insert all talent prerequisites now that all talents exist
    print(f"\nInserting talent prerequisites...")
    prereq_count = 0
    for talent_id, prereqs in talent_prerequisites.items():
        for prereq_id in prereqs:
            try:
                conn.execute("""
                    INSERT INTO talent_prerequisites (talent_id, prerequisite_id)
                    VALUES (?, ?)
                """, (talent_id, prereq_id))
                prereq_count += 1
            except Exception as e:
                print(f"  WARNING: Could not insert prerequisite {prereq_id} for talent {talent_id}: {e}")
    conn.commit()
    print(f"  Inserted {prereq_count} prerequisite relationships")

    # Collect and fetch cards
    card_ids = collect_card_ids(conn)

    print(f"\nFetching card details (0.25s delay between requests)...")
    card_success_count = 0

    for i, card_id in enumerate(card_ids):
        if fetch_and_store_card(conn, card_id, i, len(card_ids)):
            card_success_count += 1
        time.sleep(0.25)  # Rate limiting
        conn.commit()  # Commit after each card

    prune_unused_filters(conn)

    # Summary
    print("\n" + "="*60)
    print(f"COMPLETE:")
    print(f"  Talents: {talent_success_count}/{len(talent_ids)} inserted")
    print(f"  Talent Prerequisites: {prereq_count} relationships inserted")
    print(f"  Cards: {card_success_count}/{len(card_ids)} inserted")
    print(f"Database: {db_path}")
    print("="*60)

    conn.close()


if __name__ == '__main__':
    main()
