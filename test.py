from selenium import webdriver

chrome_driver_path = "C:\Development\chromedriver.exe"
opt = webdriver.ChromeOptions()
opt.add_argument('headless')
driver = webdriver.Chrome(executable_path=chrome_driver_path, options=opt)

driver.get(f"https://www.amazon.ca/Star-Revenge-Anakin-Skywalker-ARTFX/dp/B082WH2JV4/ref=dp_prsubs_1?pd_rd_i=B082WH2JV4&psc=1")

find_price = driver.find_element_by_xpath("//span[@id='priceblock_ourprice']")
find_price = find_price.text
find_price = find_price.replace("$", "")
product_price = float(find_price)

product_name = driver.find_element_by_xpath("//span[@id='productTitle']")
product_name = product_name.text

print(product_name, product_price)