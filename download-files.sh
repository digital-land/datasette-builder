#!/usr/bin/env bash

mkdir -p files

BUCKET=$1

FILES=$(aws s3api list-objects --bucket "$BUCKET" --output json --query "Contents[?ends_with(Key, 'sqlite3')]" | jq -rc '.[].Key')
for FILE in $FILES; do
  echo "Downloading $FILE"
  aws s3api get-object --bucket "$BUCKET" --key "$FILE" "./files/$(basename "$FILE")" > /dev/null
  aws s3api get-object --bucket "$BUCKET" --key "$FILE.json" "./files/$(basename "$FILE").json" > /dev/null || echo "no inspect files"
done

echo "All sqlite files downloaded successfully."

cat ./files/*.json | jq -s add > ./files/inspect-data-all.json