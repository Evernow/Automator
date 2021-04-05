from sys import path
from os import chdir
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


if __name__ == "__main__":
    chdir(path[0])
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    
    nvidiaGPU(driver)
    
    driver.close()
