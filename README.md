# Build

An oddly specific utility with a generic name.

This utility script builds Batocera images and uploads them to S3 buckets for
web hosting and data management.

# What does it do?

This script will run a build for a particular board architecture and show you 
a pretty decently functional (but imperfect) progress bar. It also logs make 
output to build.log in the build directory. It will show you a usage guide if
you ask for --help.

If the build succeeds, it will then upload the files to an s3 bucket, and 
then it will run another script to create index.html files to crawl around the
directory structure. You'll see `bucket/batocera/board/build_id/<files>`.

If you setup hosting, you can give https://bucket.example.com/batocera/board/build_id/ 
to batocera-update and it will download the root image and run the update process.

# Environment Variables

- board : Set a default board to build so you don't have to pass it in as a
  command line argument.

- default_bucket_path : Set a default bucket path for s3 uploads.

# Quirks

There are defaults hardcoded that point to my bucket and my favorite board
if no environment variable is set, so set them and stop accidentally trying
to upload to my bucket.

# Setup Notes

1. For the AWS upload to work, you will need to have initialized your AWS CLI
   environment. Go do that.

2. I recommend creating a dedicated bucket and then setting it up for web
   hosting where it will redirect to index.html etc.

3. You need python3 and to create a venv in the main directory (where the
   README.md resides).

    ```bash
    python3 -m venv venv
    . venv/bin/activate
    pip -U pip setuptools wheel
    pip install -r requirements.txt
    deactivate
    ```

4. What I do is keep this as a sister to the batocera build directory and
   invoke it like this:

    ```bash
    ../utils/build --board s922x --clean --suffix special
    ```

Feel free to put it in your path or wherever you want.