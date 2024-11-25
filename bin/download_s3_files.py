import click
import sqlite3
import urllib.request

from pathlib import Path

PARQUET_ISSUES = {
#    dataset : resource
   'article-4-direction-area':'936033805ce03700457da34ff3761ef7c305385ce3584e31dbc72c8a84298a6e'
}

@click.command()
def download_s3_files():
    # download some sample issues
    for dataset, resource in PARQUET_ISSUES.items():
        url = f"https://files.planning.data.gov.uk/log/issue/dataset={dataset}/resource={resource}/{resource}.parquet"

        # Local filename to save as
        file_name = f"{resource}.parquet"
        file_path = Path(f's3_files/log/issue/dataset={dataset}/resource={resource}') / file_name

        try:
            # Download the file
            file_path.parent.mkdir(parents=True,exist_ok=True)
            urllib.request.urlretrieve(url, file_path)
            print(f"File downloaded successfully as '{file_name}'")

        except urllib.error.URLError as e:
            print(f"Failed to download file: {str(file_path)} error: {e}")

    for db in ['digital-land.sqlite3','performance.sqlite3']:
    # finally create empty digital-land and performance files
        # Specify the name of the SQLite database file
        db_name = "files/" + db

        # Create a connection to the SQLite database
        # If the file does not exist, it will be created
        conn = sqlite3.connect(db_name)

        # Close the connection
        conn.close()
   

if __name__ == "__main__":
    download_s3_files()