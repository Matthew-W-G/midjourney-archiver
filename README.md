# Midjourney Archiver

## Description
Stores and downloads Midjourney-generated images alongside given prompts.

## Installation

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/matthew-w-g/midjourney-archiver.git
    cd midjourney-archiver
    ```

2. **Install Cookie Extension**:
    - Download [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg) (or a similar extension) from the Chrome Web Store.

3. **Set Up Cookies**:
    - Log in to the Midjourney website, navigate to the archive section, and open the cookie extension.
    - Copy the cookie data and paste it into a new file `cookies.json` inside of src/scripts/

4. **Set Up ENV file**:
    - Create new .env file in root directory
    - Set variable DOWNLOAD_FOLDER to absolute path of where you want to save images

5. **Run the Script**:
    - Run the script:

    ```bash
    ./run_script.sh
    ```
