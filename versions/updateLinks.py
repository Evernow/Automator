from sys import path
from os import chdir
from datetime import datetime
from requests import head
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
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
    downloadButton = driver.find_element_by_link_text('DOWNLOAD NOW')
    # TODO: Also get latest version. How does AMD even number driver versions?
    version = ''
    link = downloadButton.get_attribute('href')
    print('Got AMD GPU driver info! Version: ' + version + ', Link: ' + link)
    with open('amdGPU.txt', 'w') as f:
        f.write(version)
        f.write('\n')
        f.write(link)
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
