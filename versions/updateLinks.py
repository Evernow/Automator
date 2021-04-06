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
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'lnkDwnldBtn'))
        )
    except TimeoutException:
        element = None
        print('Timeout loading download page, something is up...')
        pass

    if element is not None:
        url = element.get_attribute('href').split('&')[0].split('?url=')[1]
        version = url.split('/')[2]
        # Get the actual download URL from the button link
        link = 'https://us.download.nvidia.com' + url
        with open('nvidiaGPU.txt', 'w') as f:
            f.write(version)
            f.write("\n")
            f.write(link)
            f.write("\n")
            f.write(datetime.now().strftime('%d/%m/%Y %H:%M'))

def amdGPU(driver: webdriver.Firefox):
    driver.get('https://www.amd.com/en/support')
    downloadButton = driver.find_element_by_link_text('DOWNLOAD NOW')
    # TODO: Also get latest version. How does AMD even number driver versions?
    link = downloadButton.get_attribute('href')
    with open('amdGPU.txt', 'w') as f:
        f.write('\n')
        f.write(link)
        f.write('\n')
        f.write(datetime.now().strftime('%d/%m/%Y %H:%M'))

def win10(driver: webdriver.Firefox):
    driver.get('https://winreleaseinfoprod.blob.core.windows.net/winreleaseinfoprod/en-US.html')
    # Find the latest version based on the "Microsoft recommends" text
    recommededByMSText = driver.find_element_by_id('suggested-build-flyout')
    # Get the parent of the table data element (table row)
    parent = recommededByMSText.find_element_by_xpath('..')
    # Get the first table data element, which contains the version text
    version = parent.find_element_by_xpath('*').text
    
    driver.get('https://www.microsoft.com/en-us/software-download/windows10')
    element = driver.find_element_by_id('windows10-upgrade-now')
    url = element.get_attribute('href')
    # To get the download link, we sadly have to use Requests as Selenium / the webdriver API does not contain the option to send HEAD requests
    link = head(url, allow_redirects=True).url
    with open('win10.txt', 'w') as f:
        f.write(version)
        f.write('\n')
        f.write(link)
        f.write('\n')
        f.write(datetime.now().strftime('%d/%m/%Y %H:%M'))
    

if __name__ == "__main__":
    chdir(path[0])
    options = Options()
    options.headless = True
    # Overwrite the User Agent to make sites think we're actually on Windows
    # Some sites (looking at you MS) will automatically redirect to different download links when detecting that you're on Linux
    profile = webdriver.FirefoxProfile()
    profile.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.9 Safari/537.36")
    driver = webdriver.Firefox(firefox_profile=profile, options=options)
    
    nvidiaGPU(driver)
    amdGPU(driver)
    win10(driver)
    
    driver.close()
