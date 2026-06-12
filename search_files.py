import os

paths_to_search = [
    r"c:\Users\leonm\Desktop",
    r"c:\Users\leonm\Desktop\Roadhub",
    r"c:\Users\leonm\Desktop\Roadshub",
]

for p in paths_to_search:
    if os.path.exists(p):
        print(f"Searching {p}...")
        for root, dirs, files in os.walk(p):
            # Limit depth to 2 to avoid scanning everything
            depth = root.replace(p, '').count(os.sep)
            if depth > 2:
                continue
            for f in files:
                if f in ['index.html', 'styles.css']:
                    print(f"Found {f} at: {os.path.join(root, f)}")
