import sys
import os
import time
import datetime
import requests
import logging
import packaging.version
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def nvidia_gpu(wd: webdriver.Firefox):
    logger = logging.getLogger('NvidiaGPU')
    logger.info('Getting info')

    # Load the driver download page
    wd.get('https://www.nvidia.com/Download/index.aspx')
    # Get the Select elements from the site
    selects = {
        'pType': Select(wd.find_element_by_name('selProductSeriesType')),
        'pSeries': Select(wd.find_element_by_name('selProductSeries')),
        # These are currently not used. If anyone needs them, re-enable them
        # 'product': Select(driver.find_element_by_name('selProductFamily')),
        # 'os': Select(driver.find_element_by_name('selOperatingSystem')),
        # 'dType': Select(driver.find_element_by_name('ddlDownloadTypeCrdGrd'))
    }

    selects['pType'].select_by_visible_text('GeForce')
    # Select a non-notebook driver just in case
    for option in selects['pSeries'].options:
        if 'Notebooks' not in option.text:
            selects['pSeries'].select_by_visible_text(option.text)
            break

    # Act like we pressed the submit button (easier than searching for the element, probably faster too)
    wd.execute_script('GetDriver()')

    # Wait for the new page to load and get the download button
    download_button = WebDriverWait(wd, 10).until(
        EC.presence_of_element_located((By.ID, 'lnkDwnldBtn'))
    )

    # Get the actual download URL from the button link
    url: str = download_button.get_attribute('href').split('&')[0].split('?url=')[1]
    version: str = url.split('/')[2]
    link = 'https://us.download.nvidia.com' + url
    # If we have a 'nvidiaOverride.txt' file *and* the version specified in there
    # is newer than the one we got, use that instead
    if os.path.isfile('nvidiaOverride.txt'):
        logger.info('Detected nvidiaOverride.txt')
        with open('nvidiaOverride.txt') as f:
            lines = f.read().splitlines()
            override_version = lines[0]
            override_link = lines[1]
        # Check if the version we're overriding is actually newer than the one on the site
        # In case anyone ever forgets to delete the file after the site gets updated,
        # we won't stay on the older version forever
        if packaging.version.parse(override_version) > packaging.version.parse(version):
            logger.info('OverrideVersion {} is greater than version {}'.format(override_version, version))
            version = override_version
            link = override_link
    logger.info('Got Nvidia GPU driver info! Version: {}, Link: {}'.format(version, link))
    with open('nvidiaGPU.txt', 'w') as f:
        f.write(version)
        f.write("\n")
        f.write(link)
        f.write("\n")
        f.write(datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))


def amd_gpu(wd: webdriver.Firefox):
    logger = logging.getLogger('AMD_GPU')
    logger.info('Getting info')
    wd.get('https://www.amd.com/en/support')
    # Wait for the "We use cookies" text to fade in
    time.sleep(2)
    # Try to click the button for 2 seconds
    try:
        WebDriverWait(wd, 2).until(
            EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler'))
        ).click()
    except TimeoutException:
        # For SOME REASON the "Accept all cookies" button sometimes just doesn't show up.
        # We'll click the close button then
        wd.find_element_by_class_name('onetrust-close-btn-ui').click()
    else:
        # Wait for the text to fade out again
        time.sleep(1.5)
    
    # Do the same thing for the "Do you want to take part in a short survey" box that randomly appears
    # Yes for some reason that exists
    time.sleep(1)
    try:
        WebDriverWait(wd, 1).until(
            EC.element_to_be_clickable((By.ID, 'cboxClose'))
        ).click()
    except TimeoutException:
        pass
    else:
        time.sleep(1.5)
    
    # Go through the product info selects, wait for each to become visible and select the 2nd item
    # This way we always get the newest card with, in turn, the newest drivers
    selects = {
        'pType': Select(wd.find_element_by_id('Producttype')),
        'pFamily': Select(wd.find_element_by_id('Productfamily'))
    }
    selects['pType'].select_by_index(1)
    WebDriverWait(wd, 10).until(
        EC.element_to_be_clickable((By.ID, 'Productfamily'))
    )
    selects['pFamily'].select_by_index(1)
    selects['pLine'] = Select(WebDriverWait(wd, 10).until(
        EC.presence_of_element_located((By.ID, 'Productline'))
    ))
    selects['pLine'].select_by_index(1)
    selects['pModel'] = Select(WebDriverWait(wd, 10).until(
        EC.presence_of_element_located((By.ID, 'Productmodel'))
    ))
    selects['pModel'].select_by_index(1)
    # Once we selected everything, submit the selections
    wd.find_element_by_id('edit-submit').click()
    
    # Search for the first element with the "btn-transparent-black" class, which is going to be the W10 download button
    download_button = WebDriverWait(wd, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'btn-transparent-black'))
    )
    link = download_button.get_attribute('href')
    version = link.split('/')[-1].split('-')[-4]
    
    # Since AMD is a great company and tries to block 3rd party sites from downloading their drivers,
    # we have to store the current URL and use that later as a "referer" to download the driver
    referer = wd.current_url
    
    logger.info('Got info! Version: {}, Link {}, Referrer {}'.format(version, link, referer))
    with open('amdGPU.txt', 'w') as f:
        f.write(version)
        f.write('\n')
        f.write(link)
        f.write('\n')
        f.write(referer)
        f.write('\n')
        f.write(datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))


def win10(wd: webdriver.Firefox):
    logger = logging.getLogger('Win10')
    logger.info('Getting info')
    #
    # Version info
    #
    wd.get('https://winreleaseinfoprod.blob.core.windows.net/winreleaseinfoprod/en-US.html')
    # Find the latest version based on the "Microsoft recommends" text
    recommended_by_ms_text = wd.find_element_by_id('suggested-build-flyout')
    # Get the parent of the table data element (table row)
    parent = recommended_by_ms_text.find_element_by_xpath('..')
    # Get the first table data element, which contains the version text
    version = parent.find_element_by_xpath('*').text
    logger.info('Got W10 version: {}'.format(version))
    
    #
    # ISO download link
    #
    wd.get('https://www.microsoft.com/en-us/software-download/windows10ISO')
    # Get the product edition select element
    edition_select = Select(wd.find_element_by_id('product-edition'))
    # Selecting the 2nd element here should always give us the newest version
    edition_select.select_by_index(1)
    # Click the Confirm button
    wd.find_element_by_id('submit-product-edition').click()
    # Repeat the above process for the language select
    language_select = Select(WebDriverWait(wd, 10).until(
        EC.presence_of_element_located((By.ID, 'product-languages'))
    ))
    # We're just gonna go with English here, who speaks other languages anyways /s
    language_select.select_by_visible_text('English')
    wd.find_element_by_id('submit-sku').click()
    # Get the "64-bit Download" button using CSS selectors
    # This'll probably break someday
    download_button = WebDriverWait(wd, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="x64"]'))
    )
    iso_link = download_button.get_attribute('href')
    logger.info('Got ISO link: {}'.format(iso_link))

    # We have to create a new driver with a Win User Agent for the update assistant & media creation tool
    # If we try to use the current one, MS will just redirect to the ISO download
    profile = webdriver.FirefoxProfile()
    profile.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.9 Safari/537.36"
    )
    win_driver = webdriver.Firefox(firefox_profile=profile, options=options)
    
    #
    # Update assistant link
    #
    win_driver.get('https://www.microsoft.com/en-us/software-download/windows10')
    upgrade_button = win_driver.find_element_by_id('windows10-upgrade-now')
    # To get the download link, we sadly have to use Requests as
    # Selenium / the webdriver API does not contain the option to send HEAD requests
    update_assistant_link = requests.head(upgrade_button.get_attribute('href'), allow_redirects=True).url
    logger.info('Got update assistant link: {}'.format(update_assistant_link))
    
    #
    # Media creation tool link
    #
    download_button = win_driver.find_element_by_id('windows10-downloadtool-now')
    media_creation_tool_link = requests.head(download_button.get_attribute('href'), allow_redirects=True).url
    logger.info('Got media creation tool link: {}'.format(media_creation_tool_link))
    
    win_driver.close()
    
    with open('win10.txt', 'w') as f:
        f.write(version)
        f.write('\n')
        f.write(iso_link)
        f.write('\n')
        f.write(update_assistant_link)
        f.write('\n')
        f.write(media_creation_tool_link)
        f.write('\n')
        f.write(datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))


def rufus():
    logger = logging.getLogger('Rufus')
    logger.info('Getting info')
    resp = requests.get('https://api.github.com/repos/pbatard/rufus/releases/latest')
    version: str = resp.json()['tag_name']
    assets: list[dict] = resp.json()['assets']
    # The first asset is always the non-portable executable
    link: str = assets[0]['browser_download_url']
    logger.info('Got info! Version: {}, Link: {}'.format(version, link))
    with open('rufus.txt', 'w') as f:
        f.write(version)
        f.write('\n')
        f.write(link)
        f.write('\n')
        f.write(datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))


def balena_cli():
    logger = logging.getLogger('balenaCLI')
    logger.info('Getting info')
    resp = requests.get('https://api.github.com/repos/balena-io/balena-cli/releases/latest')
    version: str = resp.json()['tag_name']
    assets: list[dict] = resp.json()['assets']
    # Get the portable Windows x64 version
    try:
        win_portable_asset = next(x for x in assets if 'windows-x64-standalone' in x['name'])
    except StopIteration:
        logger.error('Latest balenaCLI release does not ship a Windows Standalone version! Leaving version info alone')
        return
    link: str = win_portable_asset['browser_download_url']
    logger.info('Got info! Version: {}, Link: {}'.format(version, link))
    with open('balena_cli.txt', 'w') as f:
        f.write(version)
        f.write('\n')
        f.write(link)
        f.write('\n')
        f.write(datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))


if __name__ == "__main__":
    # Setup our Logging config
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s/%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    logging.info('Script started')
    # Change directory to the script location
    os.chdir(sys.path[0])
    # Enable the headless option for our Webdriver
    options = webdriver.firefox.options.Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    logging.info('WebDriver constructed. Getting info now...')
    # Start calling the respective update functions

    nvidia_gpu(driver)
    amd_gpu(driver)
    win10(driver)
    # Both Rufus and balena CLI use Github, so we can simplify the version info there
    rufus()
    balena_cli()
    
    logging.info('All links fetched & info gotten! We\'re done here!')
    driver.close()
    exit(0)
