def check_sku():
    # def randnum(fname):
    #     lines=open(fname).read().splitlines()
    #     return random.choice(lines)

    # def check_proxy_ozon():
    #     fname = 'proxy.txt'
    #     proxy = random.choice(open(fname).read().splitlines())
    #     proxies = { "https": proxy }
    #     headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}
    #     response = requests.get(f"https://www.ozon.ru/product/{sku}/", headers=headers, proxies=proxies)
    #     if 'NOINDEX, NOFOLLOW' in response.text:
    #         print(response.text)
    #         check_proxy_ozon()
    #     return response

    fname = "proxy.txt"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0"
    }
    for i in range(0, 10):
        print(i)
        proxy = random.choice(open(fname).read().splitlines())
        proxies = {"https": proxy}
        response = requests.get(
            f"https://www.ozon.ru/product/{sku}/",
            headers=headers,
            proxies=proxies,
        )
        if "NOINDEX, NOFOLLOW" in response.text:
            print(response.text)
        else:
            break
    # proxies = { "https": 'http://i17t3011126:MLKJTvkKH5@212.107.27.169:7951' }

    print(f"!!@!@!@!{response}")

    page = html.fromstring(response.text)
    title = page.xpath(".//h1/text()")[0]
    # price = re.search('(?<="price":").*?(?=")', response.text)[0]
    price = page.xpath("//div[@slot='content']//span/text()")[0]
    print(f"!!!!!!!!!!!!!!!{price}")
    cover = re.search('(?<=image":").*?(?=")', response.text)[0]
    print(f"!!!!!!!!!!!!!!!{cover[0]}")
    # cover = page.xpath("//div[@data-widget='webGallery']//img[1]/@src")
    # cover = page.xpath("//div[@data-widget='webGallery']//img[1]/@src")[0]
    # title = f"{title[0]} / {title[1]}"
    price = Helper.filter_price(price)
    product = {"title": title, "price": price, "cover": cover}
    return product