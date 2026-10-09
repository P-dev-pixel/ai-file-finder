import argparse
from pathlib import Path



from app.database import (
    add_search_root,
    get_search_roots,
    get_connection,
    initialize_database,
    search_files,
)

from app.scanner import scan_files


def index_folder(root_path: str):
    initialize_database()

    root = Path(root_path).expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(
            f"Folder does not exists: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Not a folder: {root}"
        )

    add_search_root(str(root))

    indexed = 0
    current_files = set()

    with get_connection() as connection:
        for file_data in scan_files(str(root)):
            connection.execute(
                """
                INSERT INTO files (
                    name,
                    path,
                    extension,
                    size_bytes,
                    modified_at
                )
                VALUES (
                    :name,
                    :path,
                    :extension,
                    :size_bytes,
                    :modified_at
                )
                ON CONFLICT(path) DO UPDATE SET
                    name = excluded.name,
                    extension = excluded.extension,
                    size_bytes = excluded.size_bytes,
                    modified_at = excluded.modified_at
                """,
                file_data,
            )
            current_files.add(file_data["path"])
            indexed += 1
            
            root_prefix = str(root) + "\\"     
    
            old_files = connection.execute(
               """
              SELECT path
            FROM files
            WHERE path LIKE ?
             """,
             (root_prefix + "%",),
        
        
               ).fetchall()
     
            for old_file in old_files:
               if old_file["path"] not in current_files:
         
                connection.execute(
                
                """
                DELETE FROM files
                WHERE path = ?
                """,
                (old_file["path"],),
                
            ) 
        connection.execute("""
         INSERT INTO file_search(file_search)
         VALUES ('rebuild')
         """)  

    print(f"Files processed: {indexed}")


def search_folder(query: str, limit: int, extension: str | None):
    rows = search_files(query, limit, extension)

    if not rows:
        print("No matching files found.")
        return

    print(f"\nFound {len(rows)} result(s):\n")
    
    for row in rows:
        print(f"Name: {row['name']}")
        print(f"Path: {row['path']}")
        print(f"Type: {row['extension']}")
        print(f"Size: {row['size_bytes']} bytes")
        print(f"modified {row['modified_at']}")
        print("-" * 70)



def show_search_roots():
    initialize_database()

    roots = get_search_roots()

    if not roots:
        print("No search roots configured.")
        return

    print("\nSearch roots:\n")

    for root in roots:
        print(f"{root['id']}: {root['path']}")
        
        
        

def main():
    parser = argparse.ArgumentParser(
        description="AI File Finder - V1"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    index_parser = subparsers.add_parser(
        "index",
        help="Index a folder",
    )

    index_parser.add_argument(
        "folder",
        help="Folder to scan",
    )

    search_parser = subparsers.add_parser(
        "search",
        help="Search indexed files",
    )

    search_parser.add_argument(
        "query",
        help="Search query",
    )

    search_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of results",
    )
    
    search_parser.add_argument(
        "--type",
        help="Filter by file extension, for eg .dart",
    )
    
    roots_parser = subparsers.add_parser(
    "roots",
    help="Show indexed search roots",
    )


    args = parser.parse_args()

    try:
        if args.command == "index":
            index_folder(args.folder)
            
        elif args.command == "search":
          search_folder(
             args.query,
             args.limit,
             args.type,
          )
            
        elif args.command == "roots":
            show_search_roots()

    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
