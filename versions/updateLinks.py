from sys import path
from os import chdir
from time import sleep
from datetime import datetime
from requests import head
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

def nvidiaGPU(driver: webdriver.Firefox):
    print('Getting Nvidia GPU driver info')
    # Load the driver download page
    driver.get('https://www.nvidia.com/Download/index.aspx')
    # Get the Select elements from the site
    selects = {
        'pType': Select(driver.find_element_by_name('selProductSeriesType')),
        'pSeries': Select(driver.find_element_by_name('selProductSeries')),
        # These are currently not used. If anyone needs them, re-enable them
        # 'product': Select(driver.find_element_by_name('selProductFamily')),
        # 'os': Select(driver.find_element_by_name('selOperatingSystem')),
        # 'dType': Select(driver.find_element_by_name('ddlDownloadTypeCrdGrd'))
    }
    submit_button = driver.find_element_by_id('ManualSearchButtonTD')

    selects['pType'].select_by_visible_text('GeForce')
    # Select a non-notebook driver just in case
    for option in selects['pSeries'].options:
        if 'Notebooks' not in option.text:
            selects['pSeries'].select_by_visible_text(option.text)
            break

    # Act like we pressed the submit button (easier than searching for the element, probably faster too)
    driver.execute_script('GetDriver()')

    # Wait for the new page to load and get the download button
    downloadButton = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'lnkDwnldBtn'))
    )

    # Get the actual download URL from the button link
    url = downloadButton.get_attribute('href').split('&')[0].split('?url=')[1]
    version = url.split('/')[2]
    link = 'https://us.download.nvidia.com' + url
    print('Got Nvidia GPU driver info! Version: ' + version + ', Link: ' + link)
    with open('nvidiaGPU.txt', 'w') as f:
        f.write(version)
        f.write("\n")
        f.write(link)
        f.write("\n")
        f.write(datetime.now().strftime('%d/%m/%Y %H:%M'))

def amdGPU(driver: webdriver.Firefox):
    print('Getting AMD GPU driver info')
    driver.get('https://www.amd.com/en/support')
    # Wait for the "We use cookies" text to fade in
    sleep(2)
    # Try to click the button for 2 seconds
    try:
        WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler'))
        ).click()
    except TimeoutException:
        # For SOME REASON the "Accept all cookies" button sometimes just doesn't show up.
        # We'll click the close button then
        driver.find_element_by_class_name('onetrust-close-btn-ui').click()
        pass
    else:
        # Wait for the text to fade out again
        sleep(1.5)
    
    
    # Do the same thing for the "Do you want to take part in a short survey" box that randomly appears
    # Yes for some reason that exists
    sleep(1)
    try:
        WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.ID, 'cboxClose'))
        ).click()
    except TimeoutException:
        pass
    else:
        sleep(1.5)
    
    # Go through the product info selects, wait for each to become visible and select the 2nd item
    # This way we always get the newest card with, in turn, the newest drivers
    selects = {
        'pType': Select(driver.find_element_by_id('Producttype')),
        'pFamily': Select(driver.find_element_by_id('Productfamily'))
    }
    selects['pType'].select_by_index(1)
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, 'Productfamily'))
    )
    selects['pFamily'].select_by_index(1)
    selects['pLine'] = Select(WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'Productline'))
    ))
    selects['pLine'].select_by_index(1)
    selects['pModel'] = Select(WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'Productmodel'))
    ))
    selects['pModel'].select_by_index(1)
    # Once we selected everything, submit the selections
    driver.find_element_by_id('edit-submit').click()
    
    # Search for the first element with the "btn-transparent-black" class, which is going to be the W10 download button
    downloadButton = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'btn-transparent-black'))
    )
    link = downloadButton.get_attribute('href')
    version = link.split('/')[-1].split('-')[-4]
    
    # Since AMD is a great company and tries to block 3rd party sites from downloading their drivers,
    # we have to store the current URL and use that as a "referer" to download the driver
    referer = driver.current_url
    
    print('Got AMD GPU driver info! Version: ' + version + ', Link: ' + link + ', Referer: ' + referer)
    with open('amdGPU.txt', 'w') as f:
        f.write(version)
        f.write('\n')
        f.write(link)
        f.write('\n')
        f.write(referer)
        f.write('\n')
        f.write(datetime.now().strftime('%d/%m/%Y %H:%M'))

def win10(driver: webdriver.Firefox):
    print('Getting Windows 10 info')
    #
    # Version info
    #
    driver.get('https://winreleaseinfoprod.blob.core.windows.net/winreleaseinfoprod/en-US.html')
    # Find the latest version based on the "Microsoft recommends" text
    recommededByMSText = driver.find_element_by_id('suggested-build-flyout')
    # Get the parent of the table data element (table row)
    parent = recommededByMSText.find_element_by_xpath('..')
    # Get the first table data element, which contains the version text
    version = parent.find_element_by_xpath('*').text
    print('Got W10 version: ' + version)
    
    #
    # ISO download link
    #
    driver.get('https://www.microsoft.com/en-us/software-download/windows10ISO')
    # Get the product edition select element
    editionSelect = Select(driver.find_element_by_id('product-edition'))
    # Selecting the 2nd element here should always give us the newest version
    editionSelect.select_by_index(1)
    # Click the Confirm button
    driver.find_element_by_id('submit-product-edition').click()
    # Repeat the above process for the language select
    languageSelect = Select(WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'product-languages'))
    ))
    # We're just gonna go with English here, who speaks other languages anyways /s
    languageSelect.select_by_visible_text('English')
    driver.find_element_by_id('submit-sku').click()
    # Get the "64-bit Download" button using CSS selectors
    # This'll probably break someday
    downloadButton = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="x64"]'))
    )
    ISOlink = downloadButton.get_attribute('href')
    print('Got W10 ISO link: ' + ISOlink)
    
    
    # We have to create a new driver with a Win User Agent for the update assistant & media creation tool
    # If we try to use the current one, MS will just redirect to the ISO download
    profile = webdriver.FirefoxProfile()
    profile.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.9 Safari/537.36")
    winDriver = webdriver.Firefox(firefox_profile=profile, options=options)
    
    #
    # Update assistant link
    #
    winDriver.get('https://www.microsoft.com/en-us/software-download/windows10')
    upgradeButton = winDriver.find_element_by_id('windows10-upgrade-now')
    # To get the download link, we sadly have to use Requests as Selenium / the webdriver API does not contain the option to send HEAD requests
    UAlink = head(upgradeButton.get_attribute('href'), allow_redirects=True).url
    print('Got W10 update assistant link: ' + UAlink)
    
    #
    # Media creation tool link
    #
    downloadButton = winDriver.find_element_by_id('windows10-downloadtool-now')
    MCTlink = head(downloadButton.get_attribute('href'), allow_redirects=True).url
    print('Got W10 media creation tool link: ' + MCTlink)
    
    winDriver.close()
    
    with open('win10.txt', 'w') as f:
        f.write(version)
        f.write('\n')
        f.write(ISOlink)
        f.write('\n')
        f.write(UAlink)
        f.write('\n')
        f.write(MCTlink)
        f.write('\n')
        f.write(datetime.now().strftime('%d/%m/%Y %H:%M'))
    

if __name__ == "__main__":
    print('Script started')
    chdir(path[0])
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    print('WebDriver constructed. Getting info now...')
    
    nvidiaGPU(driver)
    amdGPU(driver)
    win10(driver)
    
    print('All links fetched & info gotten! We\'re done here!')
    driver.close()
    exit(0)
