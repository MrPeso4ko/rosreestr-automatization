# -*- coding: utf8 -*-

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import visibility_of_element_located, presence_of_element_located
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, \
    StaleElementReferenceException
from time import sleep
import tkinter as tk
import re
from functools import partial
from textwrap import fill as make_paragraph
import requests
from sys import exit
import os
from json.decoder import JSONDecodeError
import twocaptcha

import zipfile
from xml.etree import cElementTree as ElementTree


# from: http://stackoverflow.com/questions/2148119/how-to-convert-an-xml-string-to-a-dictionary-in-python
class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class XmlDictConfig(dict):
    """
    Example usage:

    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:

    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)

    And then use xmldict for what it is... a dict.
    """

    def __init__(self, parent_element):
        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if element:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDictConfig(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    aDict = {element[0].tag: XmlListConfig(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                self.update({element.tag: element.text})


class Converter:
    def __init__(self, option_headless=True):
        options = webdriver.FirefoxOptions()
        # options = webdriver.ChromeOptions()
        options.headless = option_headless
        # options.add_experimental_option("prefs", {
        #     "download.default_directory": dl_dir,
        #     "download.prompt_for_download": False,
        #     "download.directory_upgrade": True,
        #     "safebrowsing.enabled": True,
        #     "savefile.default_directory": dl_dir,
        #     'profile.default_content_setting_values.automatic_downloads': 1,
        #     "profile.password_manager_enabled": False,
        #     "select_file_dialogs.allowed": False
        # })
        # options.add_argument("--disable-extensions")
        # options.add_argument("--disable-infobars")
        # options.add_argument("--safebrowsing-disable-download-protection")
        # options.add_argument("--safebrowsing-disable-extension-blacklist")
        # self.driver = webdriver.Chrome(options=options, executable_path=r"chromedriver.exe")
        profile = webdriver.FirefoxProfile("66vpwrnb.selenium")
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.helperApps.alwaysAsk.force", False)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", 'application/zip')
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference('browser.download.dir', dl_dir)
        profile.set_preference('browser.download.downloadDir', dl_dir)
        profile.set_preference('browser.download.defaultFolder', dl_dir)
        self.driver = webdriver.Firefox(options=options, executable_path=r"geckodriver.exe", firefox_profile=profile)
        self.wait = lambda selector: WebDriverWait(self.driver, 15).until(
            visibility_of_element_located((By.CSS_SELECTOR, selector)))
        self.auth()

    def get_elem(self, selector):
        self.wait(selector)
        elem = self.driver.find_element_by_css_selector(selector)
        return elem

    def auth(self):
        try:
            self.driver.get(r"https://govxml.ru")
        except TimeoutException:
            self.quit()
            self.auth()

    def load_file(self, filename):
        WebDriverWait(self.driver, 100).until(
            presence_of_element_located((By.CSS_SELECTOR, "#xml-upload > div > div > a > input[type=file]")))
        field = self.driver.find_element_by_css_selector("#xml-upload > div > div > a > input[type=file]")
        field.send_keys(r"{}\{}".format(os.getcwd(), filename))

    def wait_ready(self, count):
        print("Ожидание конвертации...")
        try:
            conv = '0'
            cnt = self.get_elem("#xml-transform-download-count")
            while int(cnt.text.split()[0]) != count:
                cnt = self.get_elem("#xml-transform-download-count")
                sleep(1)
                if cnt.text.split()[0] != conv:
                    print("Конвертировано ", cnt.text.split()[0])
                    conv = cnt.text.split()[0]
        except TimeoutException:
            self.wait("a:nth-child(4)")
        print("\nФайлы конвертированы. Скачивание...")

    def download(self):
        try:
            btn = self.get_elem("#xml-transform-download > button")
            btn.click()
        except TimeoutException:
            self.get_elem("a:nth-child(4)").click()
        sleep(2)
        zip_list = [x for x in os.listdir() if x.endswith('.zip') and x.startswith('govxml')]
        for i in zip_list:
            while True:
                try:
                    z = zipfile.ZipFile(i)
                except zipfile.BadZipfile:
                    sleep(2)
                else:
                    break

    def quit(self):
        self.driver.delete_all_cookies()


def extract_xml():
    os.chdir(dl_dir)
    zip_list = [x for x in os.listdir() if x.endswith('.zip')]
    if not zip_list:
        # exit()
        pass
    if 'raw' not in os.listdir():
        os.mkdir('raw')
    for name in zip_list:
        z = zipfile.ZipFile(name)
        z.extractall()
        z.close()
        # print(r"move {} .\raw".format(name, name))
        os.popen(r"move {} .\raw".format(name, name))
        sleep(0.05)
    zip_list = [x for x in os.listdir() if x.endswith('.zip')]
    for name in zip_list:
        try:
            z = zipfile.ZipFile(name)
            z.extractall()
            z.close()
            os.remove(name)
        except FileNotFoundError:
            pass
        sleep(0.05)
    sig_list = [x for x in os.listdir() if x.endswith('.sig')]
    for name in sig_list:
        os.remove(name)
    os.chdir(cwd)


names_dict = {}


def rename_xml():
    os.chdir(dl_dir)
    xml_list = [x for x in os.listdir() if x.endswith('.xml')]
    for name in xml_list:
        tree = ElementTree.parse(name)
        root = tree.getroot()
        xmldict = XmlDictConfig(root)
        try:
            address = xmldict['ReestrExtract']['ExtractObjectRight']['ExtractObject']['ObjectDesc']['Address']
            try:
                city = address['City']['Type'] + ' ' + address['City']['Name']
            except KeyError:
                city = ''
            try:
                street = address['Street']['Type'] + ' ' + address['Street']['Name']
            except KeyError:
                street = ''
            try:
                house = address['Level1']['Type'] + ' ' + address['Level1']['Name']
            except KeyError:
                house = ''
            try:
                apartment = address['Apartment']['Type'] + ' ' + address['Apartment']['Name']
            except KeyError:
                apartment = ''
            new_name = city + ' ' + street + ' ' + house + ' ' + apartment
        except KeyError:
            continue
        new_name = new_name.replace('/', '!')
        new_name = new_name.replace('*', '')
        # new_name = transliterate(new_name)
        # new_name += '.pdf'
        # print(name, "->", new_name)
        names_dict[name[:-4]] = new_name
    os.chdir(cwd)


def convert_xml():
    os.chdir(cwd)
    converter = Converter(False)
    os.chdir(dl_dir)
    xml_list = [x for x in os.listdir() if x.endswith('.xml')]
    for i in xml_list:
        converter.load_file(i)
    # print(names_dict)
    converter.wait_ready(len(xml_list))
    converter.download()
    converter.driver.quit()
    os.chdir(cwd)


def delete_xml():
    os.chdir(dl_dir)
    xml_list = [x for x in os.listdir() if x.endswith('.xml')]
    for name in xml_list:
        os.remove(name)
    os.chdir(cwd)


def extract_pdf():
    os.chdir(dl_dir)
    zip_list = [x for x in os.listdir() if x.endswith('.zip') and x.startswith('govxml')]
    for i in zip_list:
        z = zipfile.ZipFile(i)
        z.extractall()
        z.close()
        os.remove(i)
    pdf_list = [x for x in os.listdir() if x.endswith('.pdf')]
    for name in pdf_list:
        filename = name[11:-12]
        if filename in names_dict:
            i = 0
            while True:
                try:
                    if i == 0:
                        os.rename(name, names_dict[filename] + '.pdf')
                    else:
                        os.rename(name, names_dict[filename] + '({}).pdf'.format(i))
                except FileExistsError:
                    i += 1
                else:
                    break
    os.chdir(cwd)


def full_convert():
    try:
        print("Распаковка архивов...")
        extract_xml()
        print("Определение новых имён...")
        rename_xml()
        convert_xml()
        delete_xml()
        print("Переименовывание...")
        extract_pdf()
        print("Готово!")
    except Exception as e:
        print(
            "Возникла ошибка: {}: {}\n"
            "Удалите из папки все файлы кроме архивов с заявками и уже конвертированных заявок и "
            "конвертируйте заново.".format(e.__class__, e))
        os.chdir(cwd)


class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        canvas.bind("<MouseWheel>", on_mousewheel)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas)
        self.scrollable_frame.bind("<MouseWheel>", on_mousewheel)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set, width=770, height=500)

        canvas.grid(sticky='nesw')
        scrollbar.grid(row=0, column=1, sticky='ns')


def get_code():
    def save():
        nonlocal window, txt, code, save_code
        code = txt.get()
        save_code = "yes"
        window.destroy()
        window.quit()

    def notasave():
        nonlocal window, txt, code, save_code
        code = txt.get()
        save_code = "no"
        window.destroy()
        window.quit()

    try:
        with open('code.database', 'r') as f:
            code = f.readline()
    except FileNotFoundError:
        code = ""
        save_code = ""
        window = tk.Tk()
        title = tk.Label(window, text="Введите код авторизации")
        txt = tk.Entry(window)
        # txt.bind('<<Paste>>', '<Control-V>')
        # txt.bind("<<Copy>>", "<Control-C>")
        btn_save = tk.Button(window, text="Ввести код и сохранить для дальнейших запусков", command=save)
        btn_notsave = tk.Button(window, text="Ввести код и не сохранять", command=notasave)
        title.pack()
        txt.pack()
        btn_save.pack()
        btn_notsave.pack()
        window.mainloop()
        if save_code == "yes":
            with open('code.database', 'w') as f:
                f.write(code)
    return code


def get_api_key():
    def save():
        nonlocal window, txt, code, save_code
        code = txt.get()
        save_code = "yes"
        window.destroy()
        window.quit()

    def notasave():
        nonlocal window, txt, code, save_code
        code = txt.get()
        save_code = "no"
        window.destroy()
        window.quit()

    try:
        with open('api.database', 'r') as f:
            code = f.readline()
    except FileNotFoundError:
        code = ""
        save_code = ""
        window = tk.Tk()
        title = tk.Label(window, text="Введите ключ API ruCaptcha")
        txt = tk.Entry(window)
        # txt.bind('<<Paste>>', '<Control-V>')
        # txt.bind("<<Copy>>", "<Control-C>")
        btn_save = tk.Button(window, text="Ввести код и сохранить для дальнейших запусков", command=save)
        btn_notsave = tk.Button(window, text="Ввести код и не сохранять", command=notasave)
        title.pack()
        txt.pack()
        btn_save.pack()
        btn_notsave.pack()
        window.mainloop()
        if save_code == "yes":
            with open('api.database', 'w') as f:
                f.write(code)
    return code


cwd = os.getcwd()
dl_dir = r"C:\RosreestrDownloads"

region_codes = [
    77,
    78,
    22,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    36,
    79,
    75,
    37,
    38,
    7,
    39,
    40,
    41,
    9,
    42,
    43,
    44,
    23,
    24,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    83,
    52,
    53,
    54,
    55,
    56,
    57,
    58,
    59,
    25,
    60,
    1,
    4,
    2,
    3,
    5,
    6,
    8,
    10,
    11,
    91,
    12,
    13,
    14,
    15,
    16,
    17,
    19,
    61,
    62,
    63,
    64,
    65,
    66,
    92,
    67,
    26,
    68,
    69,
    70,
    71,
    72,
    18,
    73,
    27,
    86,
    74,
    20,
    21,
    87,
    89,
    76]
region_id = [
    145000000000,
    140000000000,
    101000000000,
    110000000000,
    111000000000,
    112000000000,
    114000000000,
    115000000000,
    117000000000,
    118000000000,
    119000000000,
    120000000000,
    199000000000,
    176000000000,
    124000000000,
    125000000000,
    183000000000,
    127000000000,
    129000000000,
    130000000000,
    191000000000,
    132000000000,
    133000000000,
    134000000000,
    103000000000,
    104000000000,
    137000000000,
    138000000000,
    141000000000,
    142000000000,
    144000000000,
    146000000000,
    147000000000,
    111100000000,
    122000000000,
    149000000000,
    150000000000,
    152000000000,
    153000000000,
    154000000000,
    156000000000,
    157000000000,
    105000000000,
    158000000000,
    179000000000,
    184000000000,
    180000000000,
    181000000000,
    182000000000,
    126000000000,
    185000000000,
    186000000000,
    187000000000,
    39100000000000,
    188000000000,
    189000000000,
    198000000000,
    190000000000,
    192000000000,
    193000000000,
    195000000000,
    160000000000,
    161000000000,
    136000000000,
    163000000000,
    164000000000,
    165000000000,
    39200000000000,
    166000000000,
    107000000000,
    168000000000,
    128000000000,
    169000000000,
    170000000000,
    171000000000,
    194000000000,
    173000000000,
    108000000000,
    171100000000,
    175000000000,
    196000000000,
    197000000000,
    177000000000,
    102000000000,
    178000000000]
region_names = [
    'Москва',
    'Санкт-Петербург',
    'Алтайский край',
    'Амурская область',
    'Архангельская область',
    'Астраханская область',
    'Белгородская область',
    'Брянская область',
    'Владимирская область',
    'Волгоградская область',
    'Вологодская область',
    'Воронежская область',
    'Еврейская А.обл.',
    'Забайкальский край',
    'Ивановская область',
    'Иркутская область',
    'Кабардино-Балкарская Республика',
    'Калининградская область',
    'Калужская область',
    'Камчатский край',
    'Карачаево-Черкесская Республика',
    'Кемеровская область',
    'Кировская область',
    'Костромская область',
    'Краснодарский край',
    'Красноярский край',
    'Курганская область',
    'Курская область',
    'Ленинградская область',
    'Липецкая область',
    'Магаданская область',
    'Московская область',
    'Мурманская область',
    'Ненецкий АО',
    'Нижегородская область',
    'Новгородская область',
    'Новосибирская область',
    'Омская область',
    'Оренбургская область',
    'Орловская область',
    'Пензенская область',
    'Пермский край',
    'Приморский край',
    'Псковская область',
    'Республика Адыгея',
    'Республика Алтай',
    'Республика Башкортостан',
    'Республика Бурятия',
    'Республика Дагестан',
    'Республика Ингушетия',
    'Республика Калмыкия',
    'Республика Карелия',
    'Республика Коми',
    'Республика Крым',
    'Республика Марий Эл',
    'Республика Мордовия',
    'Республика Саха (Якутия)',
    'Республика Северная Осетия',
    'Республика Татарстан',
    'Республика Тыва',
    'Республика Хакасия',
    'Ростовская область',
    'Рязанская область',
    'Самарская область',
    'Саратовская область',
    'Сахалинская область',
    'Свердловская область',
    'Севастополь',
    'Смоленская область',
    'Ставропольский край',
    'Тамбовская область',
    'Тверская область',
    'Томская область',
    'Тульская область',
    'Тюменская область',
    'Удмуртская Республика',
    'Ульяновская область',
    'Хабаровский край',
    'Ханты-Мансийский АО',
    'Челябинская область',
    'Чеченская Республика',
    'Чувашская Республика',
    'Чукотский АО',
    'Ямало-Ненецкий АО',
    'Ярославская область']

subreg_names = []
subreg_id = []


def get_reg_by_cad(cad):
    reg_code = int(cad.split(':')[0])
    for i in range(len(region_codes)):
        if region_codes[i] == reg_code:
            return region_names[i]


def solve_captcha(filename):
    global solver
    try:
        return solver.normal(filename, numeric=1, minLength=5, maxLength=5)
    except twocaptcha.api.ApiException as e:
        if str(e) == "ERROR_CAPTCHA_UNSOLVABLE":
            print("Капча не решена. Получение новой капчи...")
            sleep(5)
            driver.get_captcha(filename)
            return solve_captcha(filename)
        if str(e) == "ERROR_ZERO_BALANCE":
            print('На счёте недостаточно средств! Попытка повторного распознавания через 60с...')
            sleep(60)
            return solve_captcha(filename)
        print("Ошибка решения капчи: {}".format(e))
        sleep(5)
        return solve_captcha(filename)
    except twocaptcha.solver.TimeoutException:
        print("RuCaptcha не отвечает. Повторный запрос...")
        sleep(5)
        return solve_captcha(filename)
    except Exception as e:
        print("Ошибка запроса капчи. Повторный запрос... ({})".format(e))
        sleep(5)
        driver.get_captcha(filename)
        return solve_captcha(filename)


def search_by_cad(cad_list):
    global driver
    merged_cad_list = ';'.join(cad_list)
    return driver.find_objects(merged_cad_list, driver.input_cad)


def search_by_address(address_list):
    global driver
    found = []
    for i in address_list:
        found.extend(driver.find_objects(i, driver.input_address))
    return found


def search_by_address2(address_list):
    def not_none(x):
        if x is None:
            return '-'
        else:
            return x

    if not address_list or not address_list[0]['reg']:
        return []
    reg_id = ""
    for i in range(len(region_names)):
        if region_names[i] == address_list[0]['reg']:
            reg_id = str(region_id[i])
    local_subreg_id = ""
    for i in range(len(subreg_names)):
        if subreg_names[i] == address_list[0]['subreg']:
            local_subreg_id = str(subreg_id[i])
    found = {}
    for i in address_list:
        query = {"macroRegionId": reg_id, "regionId": local_subreg_id, "street": i["street"], "house": i["house"],
                 "apartment": i["apartment"],
                 "structure": i["structure"], "building": i["building"], }
        try:
            api = requests.post("http://rosreestr.ru/api/online/address/fir_objects", json=query).json()
        except JSONDecodeError:
            continue
        for j in api:
            try:
                found[j["nobjectCn"]] = requests.get(
                    "http://rosreestr.ru/api/online/fir_object/{}".format(j["objectId"])).json()
            except JSONDecodeError:
                pass
    found_data = []
    for i in found:
        data = found[i]
        found_data.append(
            {"cad": data["objectData"]["objectCn"], "type": data["objectData"]["objectName"],
             "address": data["objectData"]["objectAddress"]["mergedAddress"],
             "area": data["{}Data".format(data["type"])]["areaValue"]})
        for j in found_data[-1]:
            if j == 'area':
                if found_data[-1][j] is None:
                    found_data[-1][j] = -1
            else:
                found_data[-1][j] = not_none(found_data[-1][j])
    return found_data


def fill_text(elem, text):
    if elem.get_attribute('value') == text:
        elem.clear()
        sleep(0.5)
    while elem.get_attribute('value') != text:
        elem.click()
        elem.clear()
        elem.send_keys(text)
        sleep(0.5)


class Browser:
    def __init__(self, option_headless=False):
        options = webdriver.FirefoxOptions()
        # options = webdriver.ChromeOptions()
        options.headless = option_headless
        # options.add_experimental_option("prefs", {
        #     "download.default_directory": dl_dir,
        #     "download.prompt_for_download": False,
        #     "download.directory_upgrade": True,
        #     "safebrowsing.enabled": True,
        #     "savefile.default_directory": dl_dir,
        #     'profile.default_content_setting_values.automatic_downloads': 1,
        #     "profile.password_manager_enabled": False,
        #     "select_file_dialogs.allowed": False
        # })
        # options.add_argument("--disable-extensions")
        # options.add_argument("--disable-infobars")
        # options.add_argument("--safebrowsing-disable-download-protection")
        # options.add_argument("--safebrowsing-disable-extension-blacklist")
        # self.driver = webdriver.Chrome(options=options, executable_path=r"chromedriver.exe")
        profile = webdriver.FirefoxProfile("66vpwrnb.selenium")
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.helperApps.alwaysAsk.force", False)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", 'application/zip')
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference('browser.download.dir', dl_dir)
        profile.set_preference('browser.download.downloadDir', dl_dir)
        profile.set_preference('browser.download.defaultFolder', dl_dir)
        self.driver = webdriver.Firefox(options=options, executable_path=r"geckodriver.exe", firefox_profile=profile)
        self.queue = []
        self.now_waiting = False
        self.wait = lambda selector: WebDriverWait(self.driver, 15).until(
            visibility_of_element_located((By.CSS_SELECTOR, selector)))
        self.auth()

    def get_captcha(self, filename):
        self.get_elem('.v-horizontallayout .link .v-button-caption').click()
        sleep(1)
        self.get_elem('.v-horizontallayout .v-verticallayout img').screenshot(filename)

    def get_elem(self, selector):
        self.wait(selector)
        elem = self.driver.find_element_by_css_selector(selector)
        return elem

    def auth(self):
        try:
            self.driver.get(r"https://rosreestr.ru/wps/portal/p/cc_present/ir_egrn")
            code = get_code()
            code = code.split('-')
            self.wait(".v-textfield")
            fields = self.driver.find_elements_by_css_selector(".v-textfield")
            for i in range(5):
                fill_text(fields[i], code[i])
            self.get_elem(".v-button-normalButton").click()
            self.wait('#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > div:nth-child(1) > div > '
                      'div > div > div:nth-child(1) > div > div > div > div:nth-child(1) > div > div > div > div > '
                      'div:nth-child(1) > div > div > span > span')
        except TimeoutException:
            restart()

    def download_queries(self):
        try:
            with open("queries.database", "r") as queries_file:
                queries_old = eval(queries_file.readline())
        except FileNotFoundError:
            queries_old = set()
        except SyntaxError:
            queries_old = set()
        self.get_elem('.v-gridlayout-margin-left div:nth-child(2) .v-button-caption').click()
        self.get_elem('#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > div:nth-child(2) > div > '
                      'div > div > div:nth-child(1) > div > div > div > div:nth-child(2) > div > div > div > '
                      'div:nth-child(2) > div > div > div > div:nth-child(2) > div > div > span > span').click()
        self.wait(".v-table-cell-content-black:nth-child(1) .v-table-cell-wrapper")
        sleep(2)
        next_page_button = self.get_elem('#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > '
                                         'div:nth-child(2) > div > div > div > div:nth-child(1) > div > div > div > '
                                         'div:nth-child(4) > div > div > div > div > div:nth-child(1) > div > div > '
                                         'div > div:nth-child(5) > div > div > span > img')
        queries_new_not_ready = set()
        conv = {}
        counter = 0
        while next_page_button.get_attribute('src').split('/')[-1] != 'arrows_right_na.gif':
            sleep(2)
            new_queries = [i.text for i in self.driver.find_elements_by_css_selector(
                ".v-table-cell-content-black:nth-child(1) .v-table-cell-wrapper")]
            new_btn = self.driver.find_elements_by_css_selector(
                ".v-table-cell-content-sorted~ .v-table-cell-content-black+ .v-table-cell-content-black "
                ".v-table-cell-wrapper")
            for i in range(len(new_btn)):
                try:
                    new_btn[i] = new_btn[i].find_element_by_css_selector('a')
                except NoSuchElementException:
                    new_btn[i] = None
            new_ready = set()
            new_not_ready = set()
            for i in range(len(new_queries)):
                if not new_btn[i] is None and new_queries[i] not in conv:
                    new_ready.add(new_queries[i])
                    conv[new_queries[i]] = new_btn[i]
                else:
                    new_not_ready.add(new_queries[i])
            if not new_not_ready:
                counter += 1
            else:
                counter = 0
            queries_new_not_ready.update(new_not_ready)
            queries_download = list(new_ready & queries_old)
            while queries_download:
                i = queries_download[0]
                conv[i].click()
                sleep(0.5)
                queries_download.pop(0)
                with open('queries.database', 'w') as queries_file:
                    queries_file.write(str(queries_new_not_ready | set(queries_download)))
            if counter == 5:
                break
            next_page_button.click()

    def input_cad(self, cad):
        reg = get_reg_by_cad(cad)
        cad_in = self.get_elem(
            "#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > div:nth-child(2) > div > "
            "div > div > div:nth-child(1) > div > div > div > div:nth-child(2) > div > div > "
            "div.v-tabsheet-content > div > div > div > div > div:nth-child(2) > div > div > div > "
            "div:nth-child(1) > div > div > div > div:nth-child(1) > div > div > div > div:nth-child(1) > "
            "div > div > div > div:nth-child(1) > div > input")
        fill_text(cad_in, cad)
        reg_in = self.get_elem(
            "#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > div:nth-child(2) > div > "
            "div > div > div:nth-child(1) > div > div > div > div:nth-child(2) > div > div > "
            "div.v-tabsheet-content > div > div > div > div > div:nth-child(2) > div > div > div > "
            "div:nth-child(3) > div > div > div > div:nth-child(1) > div > div > div > div:nth-child(1) > "
            "div > div > div > div:nth-child(1) > div > div > div > div:nth-child(1) > div:nth-child(1) > "
            "div > input")
        fill_text(reg_in, reg)
        self.get_elem(".gwt-MenuItem > span:nth-child(1)").click()

    def input_address(self, address):
        self.get_elem(
            "#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > div:nth-child(2) > div > "
            "div > div > div:nth-child(1) > div > div > div > div:nth-child(2) > div > div > "
            "div.v-tabsheet-content > div > div > div > div > div:nth-child(2) > div > div > div > "
            "div:nth-child(1) > div > div > div > div:nth-child(1) > div > div > div > div:nth-child(1) > "
            "div > div > div > div:nth-child(1) > div > input").clear()
        reg_in = self.get_elem(
            "#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > div:nth-child(2) > div > "
            "div > div > div:nth-child(1) > div > div > div > div:nth-child(2) > div > div > "
            "div.v-tabsheet-content > div > div > div > div > div:nth-child(2) > div > div > div > "
            "div:nth-child(3) > div > div > div > div:nth-child(1) > div > div > div > div:nth-child(1) > "
            "div > div > div > div:nth-child(1) > div > div > div > div:nth-child(1) > div:nth-child(1) > "
            "div > input")
        fill_text(reg_in, address['reg'])
        self.get_elem(".gwt-MenuItem > span:nth-child(1)").click()
        try:
            subreg_in = self.get_elem("#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > "
                                      "div:nth-child(2) > div > div > div > div:nth-child(1) > div > div > div > "
                                      "div:nth-child(2) > div > div > div.v-tabsheet-content > div > div > div > div > "
                                      "div:nth-child(2) > div > div > div > div:nth-child(3) > div > div > div > "
                                      "div:nth-child(1) > div > div > div > div:nth-child(2) > div > div > div > "
                                      "div:nth-child(1) > div > div > div > div:nth-child(1) > div > div > input")
            fill_text(subreg_in, address['subreg'])
            self.get_elem(".gwt-MenuItem > span:nth-child(1)").click()
        except TimeoutException:
            pass
        street_in = self.get_elem("#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > "
                                  "div:nth-child(2) > div > div > div > div:nth-child(1) > div > div > div > "
                                  "div:nth-child(2) > div > div > div.v-tabsheet-content > div > div > div > div > "
                                  "div:nth-child(2) > div > div > div > div:nth-child(3) > div > div > div > "
                                  "div:nth-child(3) > div > div > div > div:nth-child(2) > div > div > div > "
                                  "div:nth-child(1) > div > div > div > div:nth-child(1) > div > input")
        fill_text(street_in, address['street'])
        house_in = self.get_elem("#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > "
                                 "div:nth-child(2) > div > div > div > div:nth-child(1) > div > div > div > "
                                 "div:nth-child(2) > div > div > div.v-tabsheet-content > div > div > div > div > "
                                 "div:nth-child(2) > div > div > div > div:nth-child(3) > div > div > div > "
                                 "div:nth-child(4) > div > div > div > div:nth-child(2) > div > div > div > "
                                 "div:nth-child(2) > div > div > div > div:nth-child(1) > div > div > div > "
                                 "div:nth-child(1) > div > input")
        fill_text(house_in, address['house'])
        apartment_in = self.get_elem('#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > '
                                     'div:nth-child(2) > div > div > div > div:nth-child(1) > div > div > div > '
                                     'div:nth-child(2) > div > div > div.v-tabsheet-content > div > div > div > div > '
                                     'div:nth-child(2) > div > div > div > div:nth-child(3) > div > div > div > '
                                     'div:nth-child(4) > div > div > div > div:nth-child(2) > div > div > div > '
                                     'div:nth-child(4) > div > div > div > div:nth-child(1) > div > div > div > '
                                     'div:nth-child(1) > div > input')
        fill_text(apartment_in, address['apartment'])

    def find_objects(self, search_data, input_function):
        self.get_elem('#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > div > div:nth-child(1) > div > '
                      'div > div > div:nth-child(1) > div > div > div > div:nth-child(1) > div > div > div > div > '
                      'div:nth-child(1) > div > div > span > span').click()
        input_function(search_data)
        self.get_elem(
            ".v-horizontallayout-borderTop > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child("
            "1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > span:nth-child(1) > "
            "span:nth-child(1)").click()
        self.wait("body > div.v-window.v-readonly > div > div > div > div.v-window-contents > div > div > div > "
                  "div:nth-child(1) > div > div > div > div:nth-child(2) > div > div > span > span")
        WebDriverWait(self.driver, 100).until_not(visibility_of_element_located(
            (By.CSS_SELECTOR, "body > div.v-window.v-readonly > div > div > div > div.v-window-contents > div > div > "
                              "div > div:nth-child(1) > div > div > div > div:nth-child(2) > div > div > span > "
                              "span")))
        self.wait("#v-Z7_01HA1A42KODT90AR30VLN22003 > div > div.v-verticallayout > "
                  "div > div:nth-child(2) > div > div > div > div:nth-child(1) > "
                  "div > div > div > div:nth-child(5) > div > div")
        sleep(1)
        found_addresses = self.driver.find_elements_by_css_selector(".v-table-cell-content-black .v-label")
        found_areas = self.driver.find_elements_by_css_selector(
            ".v-table-cell-content-black:nth-child(4) .v-table-cell-wrapper")
        found_purposes = self.driver.find_elements_by_css_selector(
            ".v-table-cell-content-black:nth-child(7) .v-table-cell-wrapper")
        found_cad = self.driver.find_elements_by_css_selector('.v-table-cell-content-cadastral_num .v-label')
        found = []
        for i in range(len(found_areas)):
            found.append({})
            found[-1]['cad'] = found_cad[i].text
            if found_purposes[i].text is None or not found_purposes[i].text:
                found[-1]['type'] = "-"
            else:
                found[-1]['type'] = found_purposes[i].text
            try:
                found[-1]['area'] = float(found_areas[i].text.split()[0])
            except IndexError:
                found[-1]['area'] = -1.0
            except ValueError:
                found[-1]['area'] = -1.0
            found[-1]['address'] = found_addresses[i].text
            found[-1]['object'] = found_addresses[i]
        return found

    def make_query_by_cad(self, cad, choice):
        obj = self.find_objects(cad, self.input_cad)[0]['object']
        obj.click()
        self.wait(".v-select-option")
        self.driver.find_elements_by_css_selector(".v-select-option")[choice - 1].click()
        captcha = self.get_elem('.v-horizontallayout .v-verticallayout img')
        captcha.screenshot("captcha.png")
        captcha_code = solve_captcha("captcha.png")
        captcha_entry = self.get_elem(".v-textfield")
        fill_text(captcha_entry, captcha_code['code'])
        self.get_elem(".blockNotTall .v-horizontallayout div div:nth-child(1) div .v-button .v-button-caption").click()
        flag = True
        while flag:
            try:
                WebDriverWait(self.driver, 5).until(
                    visibility_of_element_located((By.CSS_SELECTOR, '.f-alert-content')))
            except TimeoutException:
                try:
                    solver.report(captcha_code['captchaId'], True)
                except:
                    pass
                flag = False
            else:
                try:
                    solver.report(captcha_code['captchaId'], False)
                except:
                    pass
                self.get_captcha('captcha.png')
                captcha_code = solve_captcha('captcha.png')
                fill_text(captcha_entry, captcha_code['code'])
                self.get_elem(
                    ".blockNotTall .v-horizontallayout div div:nth-child(1) div .v-button .v-button-caption").click()
        captcha_balance.set('На счету ruCaptcha {}р.'.format(solver.balance()))
        query_num = self.get_elem(".v-label-tipFont")
        query_num = re.search(r"[0-9]+-[0-9]+", query_num.text)
        query_num = query_num.group()
        try:
            with open("queries.database", 'r') as queries_file:
                queries = eval(queries_file.readline())
        except FileNotFoundError:
            queries = set()
        queries.add(query_num)
        with open("queries.database", 'w') as queries_file:
            queries_file.write(str(queries))
        self.get_elem(".v-window-contents > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) "
                      "> div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) "
                      "> div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) "
                      "> div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > span:nth-child("
                      "1) > span:nth-child(1)").click()

    def make_query(self):
        def make(q):
            try:
                self.make_query_by_cad(q[0], q[1])
            except TimeoutException as e:
                print("Произошла ошибка ({}: {})\nПовторный запрос выписки...".format(e.__class__, e))
                try:
                    restart()
                except TimeoutException:
                    sleep(60)
                    make(q)
                make(q)
            except ElementClickInterceptedException as e:
                print("Произошла ошибка ({}: {})\nПовторный запрос выписки...".format(e.__class__, e))
                try:
                    restart()
                except TimeoutException:
                    sleep(60)
                    make(q)
                make(q)
            except Exception as e:
                print("Произошла ошибка ({}: {})\nПовторный запрос выписки...".format(e.__class__, e))
                sleep(60)
                try:
                    restart()
                except:
                    sleep(60)
                    make(q)
                make(q)

        global root, queue_text
        if self.queue:
            self.now_waiting = True
            query = self.queue.pop(0)
            queue_text.set("В очереди {} заявок".format(len(self.queue)))
            make(query)
            queue_text.set("В очереди {} заявок".format(len(self.queue)))
            with open('queue.database', 'w') as f:
                f.write(str(self.queue))
            root.after(400000, self.make_query)  # time should be 400000
        else:
            self.now_waiting = False

    def add_query(self, cad, choice, add):
        global queue_text
        self.queue.append((cad, choice, add))
        queue_text.set("В очереди {} заявок".format(len(self.queue)))
        with open('queue.database', 'w') as f:
            f.write(str(self.queue))
        if not self.now_waiting:
            root.after(5000, self.make_query)

    def load_queue(self):
        try:
            with open("queue.database", 'r') as f:
                self.queue.extend(eval(f.read()))
            self.make_query()
        except FileNotFoundError:
            pass
        except SyntaxError:
            pass

    def quit(self):
        self.driver.delete_all_cookies()


def ask_headless():
    ans = False

    def yes():
        nonlocal ans
        ans = False
        window.destroy()

    def no():
        nonlocal ans
        ans = True
        window.destroy()

    window = tk.Tk()
    btn1 = tk.Button(window, text='Да', command=yes)
    btn2 = tk.Button(window, text='Нет', command=no)
    txt = tk.Label(text="Открыть окно браузера?")
    txt.pack(fill='x')
    btn1.pack(side='left', padx=30)
    btn2.pack(side='right', padx=30)
    window.wm_protocol('WM_DELETE_WINDOW', exit)
    window.mainloop()
    return ans


def restart():
    global driver
    driver.quit()
    driver.auth()


def restart_by_btn():
    global driver
    restart()
    driver.load_queue()


def make_query():
    global driver

    def cad_search():
        nonlocal cad_txt, choice
        entry_input = cad_txt.get()
        entry_input = entry_input.replace(' ', '')
        if choice.get() == "Запросить сведения об объекте":
            choice_int = 1
        else:
            choice_int = 2
        search_list = []
        if '-' in entry_input:
            entry_input = entry_input.split('-')
            cad1 = entry_input[0].split(':')
            cad2 = entry_input[1].split(':')
            for i in range(int(cad1[-1]), int(cad2[-1]) + 1):
                entry_input = ':'.join(cad1[:-1] + [str(i)])
                search_list.append(entry_input)
        elif ';' in entry_input:
            for i in entry_input.split(';'):
                search_list.append(i)
        else:
            search_list.append(entry_input)
        while True:
            try:
                list_of_found(search_list, choice_int, search_by_cad)
            except TimeoutException:
                print("Сайт росреестра работает некорректно, повторный запрос...")
                restart()
            except Exception as e:
                print("Возникла ошибка при поиске: {}. Повторный поиск...".format(e))
                restart()
            else:
                break

    def address_search():
        if choice.get() == "Запросить сведения об объекте":
            choice_int = 1
        else:
            choice_int = 2
        try:
            reg = reg_list.get(reg_list.curselection())
        except tk.TclError:
            reg_title['bg'] = 'red'
            window.after(300, (lambda: reg_title.configure(bg='red')))
            window.after(600, (lambda: reg_title.configure(bg='light gray')))
            window.after(900, (lambda: reg_title.configure(bg='red')))
            window.after(1200, (lambda: reg_title.configure(bg='light gray')))
            return
        street = street_txt.get()
        house = house_txt.get()
        apartment = apartment_txt.get()
        search_list = []
        subreg_string = subreg.get()
        if subreg_string == '-':
            subreg_string = ''
        if '-' in apartment:
            apartment = apartment.split('-')
            for i in range(int(apartment[0]), int(apartment[1]) + 1):
                search_list.append(
                    {'reg': reg, 'street': street, 'house': house, 'apartment': str(i), "subreg": subreg_string})
        else:
            search_list.append(
                {'reg': reg, 'street': street, 'house': house, 'apartment': apartment, "subreg": subreg_string})
        while True:
            try:
                list_of_found(search_list, choice_int, search_by_address)
            except TimeoutException:
                print("Сайт росреестра работает некорректно, повторный запрос...")
                restart()
            except Exception as e:
                print("Возникла ошибка при поиске: {}. Повторный поиск...".format(e))
                restart()
            else:
                break

    def address2_search():
        if choice.get() == "Запросить сведения об объекте":
            choice_int = 1
        else:
            choice_int = 2
        try:
            reg = reg_list.get(reg_list.curselection())
        except tk.TclError:
            reg_title['bg'] = 'red'
            window.after(300, (lambda: reg_title.configure(bg='red')))
            window.after(600, (lambda: reg_title.configure(bg='light gray')))
            window.after(900, (lambda: reg_title.configure(bg='red')))
            window.after(1200, (lambda: reg_title.configure(bg='light gray')))
            return
        street = street_txt.get()
        house = house_txt.get()
        apartment = apartment_txt.get()
        building = building_txt.get()
        structure = structure_txt.get()
        search_list = []
        subreg_string = subreg.get()
        if subreg_string == '-':
            subreg_string = ''
        if '-' in apartment:
            apartment = apartment.split('-')
            for i in range(int(apartment[0]), int(apartment[1]) + 1):
                search_list.append(
                    {'reg': reg, 'street': street, 'house': house, 'apartment': str(i), 'structure': structure,
                     'building': building, "subreg": subreg_string})
        else:
            search_list.append(
                {'reg': reg, 'street': street, 'house': house, 'apartment': apartment, 'structure': structure,
                 'building': building, "subreg": subreg_string})
        list_of_found(search_list, choice_int, search_by_address2)

    def list_of_found(search_list, choice_int, search_function):
        global driver

        def mark(x):
            x['marked'] = not x['marked']
            if x['marked']:
                cnt_selected.set(cnt_selected.get() - 1)
            else:
                cnt_selected.set(cnt_selected.get() + 1)
            for obj in x['line']:
                if x['marked']:
                    obj['bg'] = 'red'
                else:
                    obj['bg'] = 'white'

        def mark_exclude(x):
            if not x['marked']:
                cnt_selected.set(cnt_selected.get() - 1)
            x['marked'] = True
            for obj in x['line']:
                obj['bg'] = 'red'

        def mark_include(x):
            if x['marked']:
                cnt_selected.set(cnt_selected.get() + 1)
            x['marked'] = False
            for obj in x['line']:
                obj['bg'] = 'white'

        def do_queries():
            for k in range(len(found_data)):
                if not found_data[k]["marked"]:
                    driver.add_query(found_data[k]['cad'], choice_int, found_data[k]['address'])

        def draw_list():
            for x in range(len(found_data)):
                cur_data = found_data[x]
                cur_line = cur_data['line']
                btn = cur_data['btn']
                for obj in range(3):
                    cur_line[obj].grid(row=x + 1, column=obj)
                btn.grid(row=x + 1, column=3)

        def sort_by(value_type):
            found_data.sort(key=lambda x: x[value_type], reverse=rev[value_type])
            rev[value_type] = not rev[value_type]
            draw_list()

        def do_type_filter_include():
            selection = [found_types[k] for k in type_filter.curselection()]
            for obj in found_data:
                if obj['type'] in selection:
                    mark_include(obj)

        def do_type_filter_exclude():
            selection = [found_types[k] for k in type_filter.curselection()]
            for obj in found_data:
                if obj['type'] in selection:
                    mark_exclude(obj)

        def mark_less_include():
            try:
                val = float(area_filter_less.get())
            except ValueError:
                area_filter_less['bg'] = 'red'
                inner_window.after(300, (lambda: area_filter_less.configure(bg='red')))
                inner_window.after(600, (lambda: area_filter_less.configure(bg='light gray')))
                inner_window.after(900, (lambda: area_filter_less.configure(bg='red')))
                inner_window.after(1200, (lambda: area_filter_less.configure(bg='light gray')))
                return
            for j in found_data:
                if j['area'] < val:
                    mark_include(j)

        def mark_less_exclude():
            try:
                val = float(area_filter_less.get())
            except ValueError:
                area_filter_less['bg'] = 'red'
                inner_window.after(300, (lambda: area_filter_less.configure(bg='red')))
                inner_window.after(600, (lambda: area_filter_less.configure(bg='light gray')))
                inner_window.after(900, (lambda: area_filter_less.configure(bg='red')))
                inner_window.after(1200, (lambda: area_filter_less.configure(bg='light gray')))
                return
            for j in found_data:
                if j['area'] < val:
                    mark_exclude(j)

        def mark_more_include():
            try:
                val = float(area_filter_more.get())
            except ValueError:
                area_filter_less['bg'] = 'red'
                inner_window.after(300, (lambda: area_filter_more.configure(bg='red')))
                inner_window.after(600, (lambda: area_filter_more.configure(bg='light gray')))
                inner_window.after(900, (lambda: area_filter_more.configure(bg='red')))
                inner_window.after(1200, (lambda: area_filter_more.configure(bg='light gray')))
                return
            for j in found_data:
                if j['area'] > val:
                    mark_include(j)

        def mark_more_exclude():
            try:
                val = float(area_filter_more.get())
            except ValueError:
                area_filter_less['bg'] = 'red'
                inner_window.after(300, (lambda: area_filter_more.configure(bg='red')))
                inner_window.after(600, (lambda: area_filter_more.configure(bg='light gray')))
                inner_window.after(900, (lambda: area_filter_more.configure(bg='red')))
                inner_window.after(1200, (lambda: area_filter_more.configure(bg='light gray')))
                return
            for j in found_data:
                if j['area'] > val:
                    mark_exclude(j)

        found_data = search_function(search_list)
        found_types = set()
        for i in found_data:
            found_types.add(i['type'])
        inner_window = tk.Toplevel()
        rev = {"address": False, "type": False, "area": False, "marked": False}
        address_sort = tk.Button(inner_window, text="По адресу", command=partial(sort_by, "address"), width=40)
        type_sort = tk.Button(inner_window, text="По типу", command=partial(sort_by, "type"), width=30)
        area_sort = tk.Button(inner_window, text="По площади", command=partial(sort_by, "area"), width=15)
        marked_sort = tk.Button(inner_window, text="По выбору", command=partial(sort_by, "marked"))
        address_sort.grid(column=0, row=0)
        type_sort.grid(column=1, row=0)
        area_sort.grid(column=2, row=0)
        marked_sort.grid(column=3, row=0)
        frame = ScrollableFrame(inner_window)
        frame.grid(row=1, columnspan=4, rowspan=9)
        table = frame.scrollable_frame
        title1 = tk.Label(table, text="Адрес", width=40)
        title2 = tk.Label(table, text="Тип", width=30)
        title3 = tk.Label(table, text="Площадь", width=15)
        title1.grid(column=0, row=0)
        title2.grid(column=1, row=0)
        title3.grid(column=2, row=0)
        objects = []
        buttons = []
        btn_do_queries = tk.Button(inner_window, text="Выполнить выбранные запросы", command=do_queries)
        btn_do_queries.grid(row=10, columnspan=4)
        title_cnt = tk.Label(inner_window, text="Всего найдено: {}".format(len(found_data)))
        title_cnt.grid(row=11, columnspan=2)
        title_cnt_selected1 = tk.Label(inner_window, text="Из них выбрано:")
        title_cnt_selected1.grid(row=11, column=2, sticky='e')
        cnt_selected = tk.IntVar()
        cnt_selected.set(len(found_data))
        title_cnt_selected2 = tk.Label(inner_window, textvariable=cnt_selected)
        title_cnt_selected2.grid(row=11, column=3, sticky='w')
        for i in range(len(found_data)):
            objects.append([tk.Label()] * 3)
            line = objects[-1]
            data = found_data[i]
            line[0] = tk.Label(table, text=make_paragraph(data['address'], width=40), relief='ridge',
                               bg='white')
            line[1] = tk.Label(table, text=make_paragraph(data['type'], width=30), relief='ridge', bg='white')
            line[2] = tk.Label(table, text=data['area'], relief='ridge', bg='white')
            data['line'] = line
            data['marked'] = False
            buttons.append(tk.Button(table, text='Исключить/Добавить', command=partial(mark, data)))
            data['btn'] = buttons[-1]
            data['ind'] = i
        draw_list()

        if not objects:
            no_objects = tk.Label(table, text="Ничего не найдено", bg='red')
            no_objects.grid(row=1, column=0, columnspan=4, sticky='we')
            btn_do_queries.grid_forget()
            title1.grid_forget()
            title2.grid_forget()
            title3.grid_forget()

        filter_title = tk.Label(inner_window, text="Фильтрация")
        filter_title.grid(row=0, column=4)
        type_filter_scroll = tk.Scrollbar(inner_window)
        type_filter_scroll.grid(row=1, column=5, sticky='ns')
        type_filter = tk.Listbox(inner_window, selectmode='multiple', width=30, yscrollcommand=type_filter_scroll.set)
        type_filter_scroll['command'] = type_filter.yview
        found_types = list(found_types)
        type_filter.insert(0, *found_types)
        type_filter.grid(row=1, column=4, sticky='wens')
        type_filter_btn1 = tk.Button(inner_window, text="Исключить выбранные типы", command=do_type_filter_exclude)
        type_filter_btn2 = tk.Button(inner_window, text="Добавить выбранные типы", command=do_type_filter_include)
        type_filter_btn1.grid(row=2, column=4)
        type_filter_btn2.grid(row=3, column=4)
        area_filter_less = tk.Entry(inner_window)
        # area_filter_less.bind('<<Paste>>', '<Control-V>')
        # area_filter_less.bind("<<Copy>>", "<Control-C>")
        area_filter_less.grid(row=4, column=4, sticky='we')
        area_filter_btn_less1 = tk.Button(inner_window, text="Исключить меньшее", command=mark_less_exclude)
        area_filter_btn_less2 = tk.Button(inner_window, text="Добавить меньшее", command=mark_less_include)
        area_filter_btn_less1.grid(row=5, column=4)
        area_filter_btn_less2.grid(row=6, column=4)
        area_filter_more = tk.Entry(inner_window)
        # area_filter_more.bind('<<Paste>>', '<Control-V>')
        # area_filter_more.bind("<<Copy>>", "<Control-C>")
        area_filter_more.grid(row=7, column=4, sticky='we')
        area_filter_btn_more1 = tk.Button(inner_window, text="Исключить большее", command=mark_more_exclude)
        area_filter_btn_more2 = tk.Button(inner_window, text="Добавить большее", command=mark_more_include)
        area_filter_btn_more1.grid(row=8, column=4)
        area_filter_btn_more2.grid(row=9, column=4)
        inner_window.mainloop()

    def clear():
        reg_title.grid_remove()
        reg_scroll.grid_remove()
        reg_list.grid_remove()
        street_title.grid_remove()
        street_txt.grid_remove()
        house_title.grid_remove()
        apartment_title.grid_remove()
        house_txt.grid_remove()
        apartment_txt.grid_remove()
        btn_address_ok.grid_remove()
        cad_title.grid_remove()
        cad_txt.grid_remove()
        ask_choice.grid_remove()
        btn_cad_ok.grid_remove()
        building_txt.grid_remove()
        structure_txt.grid_remove()
        building_title.grid_remove()
        structure_title.grid_remove()
        btn_address2_ok.grid_remove()
        subreg_title.grid_remove()
        subreg_select.grid_remove()
        btn_get_subreg.grid_remove()

    def by_cad():
        nonlocal window, cad_title, cad_txt, ask_choice, btn_cad_ok
        clear()
        cad_title.grid(row=4)
        cad_txt.grid(row=5)
        ask_choice.grid(row=6)
        btn_cad_ok.grid(row=7)

    def by_address():
        nonlocal window
        clear()
        reg_title.grid(columnspan=2, row=4)
        reg_scroll.grid(column=2, sticky='ns', row=5)
        reg_list.grid(sticky='we', columnspan=2, row=5)
        subreg_title.grid(row=6)
        subreg_select.grid(row=7)
        btn_get_subreg.grid(row=6, rowspan=2, column=1)
        street_title.grid(columnspan=2, row=8)
        street_txt.grid(columnspan=2, row=9)
        house_title.grid(row=10)
        apartment_title.grid(column=1, row=10)
        house_txt.grid(row=11)
        apartment_txt.grid(column=1, row=11)
        ask_choice.grid(columnspan=2, row=12)
        btn_address_ok.grid(columnspan=2, row=13)

    def by_address2():
        clear()
        reg_title.grid(columnspan=2, row=4)
        reg_scroll.grid(column=2, sticky='ns', row=5)
        reg_list.grid(sticky='we', columnspan=2, row=5)
        subreg_title.grid(row=6)
        subreg_select.grid(row=7)
        btn_get_subreg.grid(row=6, rowspan=2, column=1)
        street_title.grid(columnspan=2, row=8)
        street_txt.grid(columnspan=2, row=9)
        house_title.grid(row=10)
        apartment_title.grid(column=1, row=10)
        house_txt.grid(row=11)
        apartment_txt.grid(column=1, row=11)
        building_title.grid(row=12)
        building_txt.grid(row=13)
        structure_title.grid(column=1, row=12)
        structure_txt.grid(column=1, row=13)
        ask_choice.grid(columnspan=2, row=14)
        btn_address2_ok.grid(columnspan=2, row=15)

    def get_subreg():
        global subreg_names, subreg_id
        nonlocal window, subreg_select
        try:
            reg = reg_list.get(reg_list.curselection())
        except tk.TclError:
            reg_title['bg'] = 'red'
            window.after(300, (lambda: reg_title.configure(bg='red')))
            window.after(600, (lambda: reg_title.configure(bg='light gray')))
            window.after(900, (lambda: reg_title.configure(bg='red')))
            window.after(1200, (lambda: reg_title.configure(bg='light gray')))
            return
        subreg_list = []
        for i in range(len(region_names)):
            if region_names[i] == reg:
                subreg_list = requests.get(r"http://rosreestr.ru/api/online/regions/{}".format(region_id[i])).json()
                break
        subreg_names = []
        subreg_id = []
        for i in range(len(subreg_list)):
            subreg_names.append(subreg_list[i]["name"])
            subreg_id.append(subreg_list[i]["id"])
        subreg.set(subreg_names[0])
        subreg_select.grid_remove()
        subreg_select = tk.OptionMenu(window, subreg, *(['-'] + subreg_names))
        subreg_select.grid(row=7)

    window = tk.Toplevel()
    main_title = tk.Label(window, text="Сделать запрос(ы)")
    main_title.grid(row=0)
    btn_cad = tk.Button(window, text="По кадастровому номеру", command=by_cad)
    btn_cad.grid(row=1)
    btn_address = tk.Button(window, text="По адресу", command=by_address)
    btn_address.grid(row=2)
    btn_address2 = tk.Button(window, text="По адресу(2)", command=by_address2)
    btn_address2.grid(row=3)
    cad_title = tk.Label(window, text="Введите кадастровый номер, или диапазон через \"-\":")
    cad_txt = tk.Entry(window, width=40)
    # cad_txt.bind('<<Paste>>', '<Control-V>')
    # cad_txt.bind("<<Copy>>", "<Control-C>")
    btn_cad_ok = tk.Button(window, text="OK", command=cad_search)
    choice = tk.StringVar(window)
    choice.set("Запросить сведения о переходе прав на объект")
    ask_choice = tk.OptionMenu(window, choice, "Запросить сведения об объекте",
                               "Запросить сведения о переходе прав на объект")
    reg_title = tk.Label(window, text="Выберите регион", bg='light gray')
    reg_scroll = tk.Scrollbar(window)
    reg_list = tk.Listbox(window, width=40, yscrollcommand=reg_scroll.set)
    reg_list.insert(0, *region_names)
    reg_scroll['command'] = reg_list.yview
    street_title = tk.Label(window, text="Название улицы")
    street_txt = tk.Entry(window, width=40)
    # street_txt.bind('<<Paste>>', '<Control-V>')
    # street_txt.bind("<<Copy>>", "<Control-C>")
    house_title = tk.Label(window, text="Номер дома")
    house_txt = tk.Entry(window, width=20)
    # house_txt.bind('<<Paste>>', '<Control-V>')
    # house_txt.bind("<<Copy>>", "<Control-C>")
    apartment_title = tk.Label(window, text="Квартира(ы)")
    apartment_txt = tk.Entry(window, width=20)
    # apartment_txt.bind('<<Paste>>', '<Control-V>')
    # apartment_txt.bind("<<Copy>>", "<Control-C>")
    building_title = tk.Label(window, text="Корпус")
    structure_title = tk.Label(window, text="Строение")
    building_txt = tk.Entry(window, width=20)
    # building_txt.bind('<<Paste>>', '<Control-V>')
    # building_txt.bind("<<Copy>>", "<Control-C>")
    structure_txt = tk.Entry(window, width=20)
    # structure_txt.bind('<<Paste>>', '<Control-V>')
    # structure_txt.bind("<<Copy>>", "<Control-C>")
    btn_address_ok = tk.Button(window, text="OK", command=address_search)
    btn_address2_ok = tk.Button(window, text="OK", command=address2_search)
    btn_get_subreg = tk.Button(window, text="Получить районы", command=get_subreg)
    subreg_title = tk.Label(window, text="Район")
    subreg = tk.StringVar(window)
    subreg.set('-')
    subreg_select = tk.OptionMenu(window, subreg, '-')
    window.mainloop()


def check_queries():
    global driver
    try:
        driver.download_queries()
    except TimeoutException:
        restart()
        check_queries()
    except StaleElementReferenceException:
        restart()
        check_queries()


def save_new_code():
    def ok():
        code = txt.get()
        with open('code.database', 'w') as f:
            f.write(code)
        window.destroy()
        window.quit()

    window = tk.Toplevel()
    title = tk.Label(window, text="Введите код авторизации:")
    txt = tk.Entry(window, width=40)
    # txt.bind('<<Paste>>', '<Control-V>')
    # txt.bind("<<Copy>>", "<Control-C>")
    btn = tk.Button(window, text="OK", command=ok)
    title.grid(row=1)
    txt.grid(row=2)
    btn.grid(row=3)
    window.mainloop()


def queue_manager():
    def draw_list():
        for x in range(len(queue_list)):
            queue_list[x]["obj"].grid(row=x)

    def move(ind):
        queue_list.insert(0, queue_list.pop(ind))
        draw_list()

    window = tk.Tk()
    frame = ScrollableFrame(window)
    frame.grid()
    inner_frame = frame.scrollable_frame
    queue_list = []
    for i in range(len(driver.queue)):
        queue_list.append({})
        try:
            queue_list[-1]["obj"] = tk.Label(inner_frame, text=make_paragraph(driver.queue[i][2]))
        except IndexError:
            queue_list[-1]["obj"] = tk.Label(inner_frame,
                                             text=make_paragraph("Адрес не указан ({})".format(driver.queue[i][0])))
        queue_list[-1]["q"] = driver.queue[i]
        tk.Button(inner_frame, text="Переместить в начало", command=partial(move, i)).grid(row=i, column=1)
    driver.queue = []
    draw_list()
    window.mainloop()
    for i in queue_list:
        driver.add_query(*i["q"])


if __name__ == '__main__':
    key = get_api_key()
    solver = twocaptcha.TwoCaptcha(key)
    headless = ask_headless()
    driver = Browser(headless)
    print(r'Файлы будут сохраняться в {}'.format(dl_dir))
    root = tk.Tk()
    btn_query = tk.Button(root, text="Сделать запрос(ы)", command=make_query)
    btn_check = tk.Button(root, text="Проверить заявки и скачать новые", command=check_queries)
    btn_code = tk.Button(root, text="Сохранить новый код авторизации", command=save_new_code)
    btn_restart = tk.Button(root, text="Перезапустить браузер", command=restart_by_btn)
    btn_check.pack()
    btn_query.pack()
    btn_code.pack()
    btn_restart.pack()
    queue_text = tk.StringVar()
    queue_text.set("В очереди нет заявок")
    queue_title = tk.Label(root, textvariable=queue_text)
    queue_title.pack()
    captcha_balance = tk.StringVar()
    captcha_balance.set("На счету ruCaptcha {}р.".format(solver.balance()))
    captcha_balance_title = tk.Label(root, textvariable=captcha_balance)
    captcha_balance_title.pack()
    btn_convert = tk.Button(root, text="Конвертировать загрузки в PDF", command=full_convert)
    btn_convert.pack()
    btn_manager = tk.Button(root, text="Менеджер очереди", command=queue_manager)
    btn_manager.pack()
    check_queries()
    driver.load_queue()
    root.mainloop()
    check_queries()
    driver.quit()
    driver.driver.quit()
