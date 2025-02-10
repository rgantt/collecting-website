#!/bin/bash

# Get the ETag of the local games.db if it exists
if [ -f games.db ]; then
    LOCAL_ETAG=$(aws s3api head-object --bucket collecting-tools-gantt-pub --key games.db --query ETag --output text 2>/dev/null || echo "")
    if [ ! -z "$LOCAL_ETAG" ]; then
        echo "Checking if games.db needs updating..."
        ERROR_MSG=$(aws s3api get-object --bucket collecting-tools-gantt-pub --key games.db --if-none-match $LOCAL_ETAG games.db 2>&1)
        if [[ $ERROR_MSG == *"Not Modified"* ]]; then
            echo "Local games.db is already up to date"
            DOWNLOAD_STATUS=304
        elif [[ $ERROR_MSG == "" ]]; then
            echo "Downloaded newer version of games.db"
            DOWNLOAD_STATUS=0
        else
            echo "Error checking games.db: $ERROR_MSG"
            DOWNLOAD_STATUS=1
        fi
    else
        echo "Downloading games.db from S3..."
        aws s3api get-object --bucket collecting-tools-gantt-pub --key games.db games.db >/dev/null
        DOWNLOAD_STATUS=$?
    fi
else
    echo "Downloading games.db from S3..."
    aws s3api get-object --bucket collecting-tools-gantt-pub --key games.db games.db >/dev/null
    DOWNLOAD_STATUS=$?
fi

if [ $DOWNLOAD_STATUS -eq 0 ] || [ $DOWNLOAD_STATUS -eq 304 ]; then
    # Deploy to Elastic Beanstalk test environment
    echo "Deploying to test environment..."
    eb deploy test
else
    echo "Failed to download/check games.db from S3"
    exit 1
fi
