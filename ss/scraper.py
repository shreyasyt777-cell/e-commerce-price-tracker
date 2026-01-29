import re
import time
import random
import requests
from urllib.parse import urlparse, urljoin, quote_plus
from bs4 import BeautifulSoup

class ProductScraper:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        self.session = requests.Session()
    
    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
    
    def normalize_url(self, url):
        if not url:
            return None
        
        url = url.strip()
        
        if not url.startswith('http://') and not url.startswith('https://'):
            if url.startswith('www.'):
                url = 'https://' + url
            elif 'amazon' in url.lower() or 'flipkart' in url.lower():
                url = 'https://' + url
            else:
                url = 'https://' + url
        
        if url.startswith('http://'):
            url = url.replace('http://', 'https://', 1)
        
        return url
    
    def extract_price(self, price_text):
        if not price_text:
            return None
        # Clean the price text
        price_text = price_text.replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
        # Find all numbers in the text
        match = re.search(r'(\d+(?:\.\d{1,2})?)', price_text)
        if match:
            try:
                price = float(match.group(1))
                # Sanity check: price should be between 1 and 10,000,000
                if 1 <= price <= 10000000:
                    return price
            except ValueError:
                pass
        return None
    
    def scrape_amazon(self, url):
        url = self.normalize_url(url)
        result = {
            'name': None,
            'price': None,
            'original_price': None,
            'image': None,
            'url': url,
            'success': False
        }
        
        if not url:
            return result
        
        try:
            print(f"Scraping Amazon URL: {url}")
            
            headers = self.get_headers()
            # Derive Host/Referer from the actual URL instead of hard-coding amazon.in,
            # so that shortened links (amzn.in, amzn.to, etc.) and other subdomains work reliably.
            parsed = urlparse(url)
            host = parsed.netloc or 'www.amazon.in'
            headers.update({
                'Host': host,
                'Referer': f"{parsed.scheme or 'https'}://{host}/",
                'DNT': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            })
            
            # Add delay to avoid rate limiting
            time.sleep(random.uniform(2, 4))
            
            response = self.session.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Check if Amazon is showing a CAPTCHA or robot check
            if 'api-services-support@amazon.com' in response.text or 'Robot Check' in response.text or 'Enter the characters you see below' in response.text:
                print("WARNING: Amazon is showing a CAPTCHA/Robot Check page")
                # Try one more time with different headers
                time.sleep(random.uniform(3, 6))
                headers['User-Agent'] = random.choice(self.user_agents)
                response = self.session.get(url, headers=headers, timeout=30, allow_redirects=True)
                
                # Check again
                if 'api-services-support@amazon.com' in response.text or 'Robot Check' in response.text:
                    result['error'] = 'Amazon blocked the request. Please try again in a few minutes.'
                    return result
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Debug: Save HTML to check structure
            # Uncomment this to see what Amazon is actually returning
            with open('debug_amazon.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Saved Amazon response to debug_amazon.html (first 500 chars): {response.text[:500]}")
            
            # Try multiple title selectors with more variations
            title_selectors = [
                ('span', {'id': 'productTitle'}),
                ('h1', {'id': 'title'}),
                ('span', {'class': 'product-title-word-break'}),
                ('h1', {'class': 'a-size-large'}),
                ('span', {'class': 'a-size-large product-title-word-break'}),
                ('div', {'id': 'titleSection'}),
                ('div', {'id': 'title_feature_div'}),
            ]
            
            for tag, attrs in title_selectors:
                if result['name']:
                    break
                elems = soup.find_all(tag, attrs)
                for elem in elems:
                    name = elem.get_text().strip()
                    if name and len(name) > 5 and len(name) < 500:
                        result['name'] = name
                        print(f"Found title using {tag} {attrs}: {name[:50]}...")
                        break
            
            # If still no name, try finding any h1 or span with product-like text
            if not result['name']:
                h1_tags = soup.find_all('h1')
                for h1 in h1_tags:
                    text = h1.get_text().strip()
                    if text and len(text) > 10 and len(text) < 300:
                        result['name'] = text
                        print(f"Found title from h1 tag: {text[:50]}...")
                        break
            
            # Try meta tags as fallback
            if not result['name']:
                meta_title = soup.find('meta', {'name': 'title'})
                if meta_title and meta_title.get('content'):
                    result['name'] = meta_title['content'].strip()
                    print(f"Found title from meta tag: {result['name'][:50]}...")
                else:
                    og_title = soup.find('meta', {'property': 'og:title'})
                    if og_title and og_title.get('content'):
                        result['name'] = og_title['content'].strip()
                        print(f"Found title from og:title: {result['name'][:50]}...")
            
            # Enhanced price extraction with more selectors
            price_found = False
            
            # Try to find price in structured data
            price_divs = soup.find_all('div', {'id': re.compile(r'price', re.I)})
            for div in price_divs:
                if price_found:
                    break
                price_spans = div.find_all('span', class_=re.compile(r'a-price-whole|a-offscreen'))
                for span in price_spans:
                    price_text = span.get_text()
                    extracted = self.extract_price(price_text)
                    if extracted and extracted > 0:
                        result['price'] = extracted
                        price_found = True
                        print(f"Found price from price div: ₹{extracted}")
                        break
            
            # Try common price selectors
            if not price_found:
                price_selectors = [
                    ('span', {'class': 'a-price-whole'}),
                    ('span', {'id': 'priceblock_ourprice'}),
                    ('span', {'id': 'priceblock_dealprice'}),
                    ('span', {'id': 'priceblock_saleprice'}),
                    ('span', {'class': 'a-offscreen'}),
                    ('span', {'class': 'a-price aok-align-center reinventPricePriceToPayMargin priceToPay'}),
                    ('span', {'id': 'tp_price_block_total_price_ww'}),
                    ('td', {'class': 'a-span12 a-color-price a-size-base'}),
                ]
                
                for tag, attrs in price_selectors:
                    if price_found:
                        break
                    elems = soup.find_all(tag, attrs)
                    for elem in elems:
                        price_text = elem.get_text()
                        extracted = self.extract_price(price_text)
                        if extracted and extracted > 0:
                            result['price'] = extracted
                            price_found = True
                            print(f"Found price using {tag} {attrs}: ₹{extracted}")
                            break
            
            # Try all a-price spans as fallback
            if not price_found:
                all_price_spans = soup.find_all('span', class_=re.compile(r'a-price'))
                for span in all_price_spans:
                    whole = span.find('span', class_='a-price-whole')
                    if whole:
                        extracted = self.extract_price(whole.get_text())
                        if extracted and extracted > 0:
                            result['price'] = extracted
                            price_found = True
                            print(f"Found price from a-price span: ₹{extracted}")
                            break
            
            # Try finding price in any span with currency symbol
            if not price_found:
                all_spans = soup.find_all('span')
                for span in all_spans:
                    text = span.get_text()
                    if '₹' in text or 'Rs' in text:
                        extracted = self.extract_price(text)
                        if extracted and extracted > 10:  # Sanity check for reasonable price
                            result['price'] = extracted
                            price_found = True
                            print(f"Found price from span with currency: ₹{extracted}")
                            break
            
            # Original price
            orig_price_elems = soup.find_all('span', {'class': re.compile(r'a-text-price')})
            for elem in orig_price_elems:
                orig_span = elem.find('span', {'class': 'a-offscreen'})
                if orig_span:
                    extracted = self.extract_price(orig_span.get_text())
                    if extracted and extracted > 0:
                        result['original_price'] = extracted
                        break
            
            # Image extraction with more methods
            img_selectors = [
                ('img', {'id': 'landingImage'}),
                ('img', {'id': 'imgBlkFront'}),
                ('img', {'id': 'ebooksImgBlkFront'}),
                ('img', {'class': re.compile(r'a-dynamic-image')}),
                ('div', {'id': 'imgTagWrapperId'}),
                ('div', {'id': 'main-image-container'}),
            ]
            
            for tag, attrs in img_selectors:
                if result['image']:
                    break
                elem = soup.find(tag, attrs)
                if elem:
                    # Check if it's an img tag
                    if elem.name == 'img':
                        if elem.get('data-old-hires'):
                            result['image'] = elem['data-old-hires']
                        elif elem.get('data-a-dynamic-image'):
                            # Parse JSON to get first image URL
                            try:
                                import json
                                img_data = json.loads(elem.get('data-a-dynamic-image'))
                                if img_data:
                                    result['image'] = list(img_data.keys())[0]
                            except:
                                pass
                        elif elem.get('src'):
                            src = elem['src']
                            if 'images-amazon' in src or 'ssl-images-amazon' in src:
                                result['image'] = src
                    # Check if it's a div containing img
                    elif elem.name == 'div':
                        img = elem.find('img')
                        if img:
                            if img.get('data-old-hires'):
                                result['image'] = img['data-old-hires']
                            elif img.get('src'):
                                result['image'] = img['src']
            
            # Try meta og:image as fallback
            if not result['image']:
                og_image = soup.find('meta', {'property': 'og:image'})
                if og_image and og_image.get('content'):
                    result['image'] = og_image['content']
            
            if result['name'] and result['price']:
                result['success'] = True
                print(f"Successfully scraped Amazon: {result['name'][:50]}... - ₹{result['price']}")
            else:
                print(f"Failed to scrape Amazon - Name: {bool(result['name'])}, Price: {bool(result['price'])}")
                if not result['name']:
                    print("  Could not find product title")
                if not result['price']:
                    print("  Could not find product price")
                    
        except Exception as e:
            print(f"Amazon scraping error: {e}")
            import traceback
            traceback.print_exc()
            result['error'] = str(e)
        
        return result
    
    def scrape_flipkart(self, url):
        url = self.normalize_url(url)
        result = {
            'name': None,
            'price': None,
            'original_price': None,
            'image': None,
            'url': url,
            'success': False
        }
        
        if not url:
            return result
        
        try:
            print(f"Scraping Flipkart URL: {url}")
            
            headers = self.get_headers()
            # Use the actual host from the URL so that shortened/redirect links work.
            parsed = urlparse(url)
            host = parsed.netloc or 'www.flipkart.com'
            headers['Host'] = host
            
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Enhanced title extraction
            title_selectors = [
                ('span', {'class': 'VU-ZEz'}),
                ('span', {'class': 'B_NuCI'}),
                ('h1', {'class': 'yhB1nd'}),
                ('span', {'class': '_35KyD6'}),
                ('h1', {'class': '_6EBuvT'}),
            ]
            
            for tag, attrs in title_selectors:
                if result['name']:
                    break
                elem = soup.find(tag, attrs)
                if elem:
                    name = elem.get_text().strip()
                    if name and len(name) > 5:
                        result['name'] = name
                        break
            
            if not result['name']:
                h1_tags = soup.find_all('h1')
                for h1 in h1_tags:
                    text = h1.get_text().strip()
                    if text and len(text) > 10 and len(text) < 300:
                        result['name'] = text
                        break
            
            # Enhanced price extraction with more selectors
            price_selectors = [
                ('div', {'class': 'Nx9bqj CxhGGd'}),
                ('div', {'class': '_30jeq3 _16Jk6d'}),
                ('div', {'class': '_30jeq3'}),
                ('div', {'class': '_25b18c'}),
                ('div', {'class': 'CEmiEU'}),
                ('div', {'class': 'hl05eU'}),
                ('div', {'class': '_16Jk6d'}),
            ]
            
            for tag, attrs in price_selectors:
                if result['price']:
                    break
                elem = soup.find(tag, attrs)
                if elem:
                    extracted = self.extract_price(elem.get_text())
                    if extracted and extracted > 0:
                        result['price'] = extracted
                        print(f"Found Flipkart price using {tag} {attrs}: ₹{extracted}")
                        break
            
            # Try finding divs with common price class patterns
            if not result['price']:
                price_divs = soup.find_all('div', class_=re.compile(r'Nx9bqj|_30jeq3|_25b18c|hl05eU|_16Jk6d'))
                for div in price_divs:
                    extracted = self.extract_price(div.get_text())
                    if extracted and extracted > 0:
                        result['price'] = extracted
                        print(f"Found Flipkart price from regex match: ₹{extracted}")
                        break
            
            # Try all divs containing rupee symbol (but be more selective)
            if not result['price']:
                all_divs = soup.find_all('div')
                for div in all_divs:
                    # Get only the direct text of this div, not nested children
                    text = ''.join(div.find_all(text=True, recursive=False))
                    if '₹' in text:
                        # Skip if it's a very long text (likely not just price)
                        if len(text.strip()) < 30:
                            extracted = self.extract_price(text)
                            if extracted and extracted > 10:  # Sanity check
                                result['price'] = extracted
                                print(f"Found Flipkart price from div with ₹: ₹{extracted}")
                                break
            
            # Last resort: check meta tags
            if not result['price']:
                og_price = soup.find('meta', {'property': 'product:price:amount'})
                if og_price and og_price.get('content'):
                    extracted = self.extract_price(og_price['content'])
                    if extracted and extracted > 0:
                        result['price'] = extracted
                        print(f"Found Flipkart price from meta tag: ₹{extracted}")
            
            # Original price
            orig_price_selectors = [
                ('div', {'class': 'yRaY8j A6+E6v'}),
                ('div', {'class': '_3I9_wc _2p6lqe'}),
                ('div', {'class': '_3I9_wc'}),
            ]
            
            for tag, attrs in orig_price_selectors:
                if result['original_price']:
                    break
                elem = soup.find(tag, attrs)
                if elem:
                    extracted = self.extract_price(elem.get_text())
                    if extracted and extracted > 0:
                        result['original_price'] = extracted
                        break
            
            # Enhanced image extraction
            img_selectors = [
                ('img', {'class': 'DByuf4 IZexXJ jLEJ7H'}),
                ('img', {'class': '_396cs4'}),
                ('img', {'class': '_2r_T1I'}),
                ('img', {'class': 'q6DClP'}),
                ('img', {'class': '_53J4C-'}),
            ]
            
            for tag, attrs in img_selectors:
                if result['image']:
                    break
                elem = soup.find(tag, attrs)
                if elem and elem.get('src'):
                    src = elem['src']
                    if 'rukminim' in src or 'static-assets' in src:
                        result['image'] = src
                        break
            
            if not result['image']:
                img_containers = soup.find_all('div', class_=re.compile(r'_3kidJX|_2SmCp5'))
                for container in img_containers:
                    img = container.find('img')
                    if img and img.get('src'):
                        src = img['src']
                        if 'rukminim' in src or 'static-assets' in src:
                            result['image'] = src
                            break
            
            if not result['image']:
                all_imgs = soup.find_all('img')
                for img in all_imgs:
                    src = img.get('src', '')
                    if 'rukminim' in src or 'static-assets' in src:
                        result['image'] = src
                        break
            
            if result['name'] and result['price']:
                result['success'] = True
                print(f"Successfully scraped Flipkart: {result['name'][:50]}... - ₹{result['price']}")
            else:
                print(f"Failed to scrape Flipkart - Name: {bool(result['name'])}, Price: {bool(result['price'])}")
                if not result['name']:
                    print("  Could not find product title")
                if not result['price']:
                    print("  Could not find product price")
                    
        except Exception as e:
            print(f"Flipkart scraping error: {e}")
            import traceback
            traceback.print_exc()
            result['error'] = str(e)
        
        return result
    
    def identify_platform(self, url):
        """Return 'amazon' or 'flipkart' based on the URL.

        This is intentionally a bit more flexible so that it also works with
        common short domains like amzn.in / amzn.to and fkrt.it.
        """
        if not url:
            return None

        url = self.normalize_url(url)
        parsed = urlparse(url)
        host = (parsed.netloc or '').lower()

        # Handle full domains and common shorteners for Amazon
        if 'amazon' in host or host.startswith('amzn.'):
            return 'amazon'

        # Handle full domains and shorteners for Flipkart
        if 'flipkart' in host or host.endswith('fkrt.it') or host.endswith('dl.flipkart.com'):
            return 'flipkart'

        return None
    
    def scrape_product(self, url):
        url = self.normalize_url(url)
        platform = self.identify_platform(url)
        if platform == 'amazon':
            return self.scrape_amazon(url), platform
        elif platform == 'flipkart':
            return self.scrape_flipkart(url), platform
        return None, None
    
    def search_flipkart_for_product(self, product_name):
        search_query = quote_plus(' '.join(product_name.split()[:5]))
        search_url = f"https://www.flipkart.com/search?q={search_query}"
        
        try:
            print(f"Searching Flipkart for: {product_name[:50]}...")
            
            headers = self.get_headers()
            headers['Host'] = 'www.flipkart.com'
            
            response = self.session.get(search_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            link_selectors = [
                ('a', {'class': 'CGtC98'}),
                ('a', {'class': '_1fQZEK'}),
                ('a', {'class': 's1Q9rs'}),
                ('a', {'class': '_2rpwqI'}),
                ('a', {'class': 'IRpwTa'}),
                ('a', {'class': 'rPDeLR'}),
                ('a', {'class': 'wjcEIp'}),
            ]
            
            product_link = None
            for tag, attrs in link_selectors:
                if product_link:
                    break
                product_link = soup.find(tag, attrs)
            
            if not product_link:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if '/p/' in href and 'pid=' in href:
                        product_link = link
                        break
            
            if product_link and product_link.get('href'):
                href = product_link['href']
                if href.startswith('/'):
                    product_url = 'https://www.flipkart.com' + href
                else:
                    product_url = href
                print(f"Found Flipkart product: {product_url[:80]}...")
                return self.scrape_flipkart(product_url)
            
            print("No matching product found on Flipkart")
                
        except Exception as e:
            print(f"Flipkart search error: {e}")
        
        return None
    
    def search_amazon_for_product(self, product_name):
        search_query = quote_plus(' '.join(product_name.split()[:5]))
        search_url = f"https://www.amazon.in/s?k={search_query}"
        
        try:
            print(f"Searching Amazon for: {product_name[:50]}...")
            
            headers = self.get_headers()
            headers['Host'] = 'www.amazon.in'
            
            response = self.session.get(search_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            product_link = None
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if '/dp/' in href or '/gp/product/' in href:
                    product_link = link
                    break
            
            if product_link and product_link.get('href'):
                href = product_link['href']
                if href.startswith('/'):
                    product_url = 'https://www.amazon.in' + href
                else:
                    product_url = href
                print(f"Found Amazon product: {product_url[:80]}...")
                return self.scrape_amazon(product_url)
            
            print("No matching product found on Amazon")
                
        except Exception as e:
            print(f"Amazon search error: {e}")
        
        return None

    def search_flipkart_products(self, product_name, max_results=24):
        """Search Flipkart by name and return a list of lightweight product dicts.

        This parses the listing cards directly instead of re-scraping each product
        page, which is faster and more reliable for a search UI.
        """
        search_query = quote_plus(' '.join(product_name.split()[:5]))
        search_url = f"https://www.flipkart.com/search?q={search_query}"
        results = []
        
        try:
            print(f"Searching Flipkart for multiple products: {product_name[:50]}...")
            headers = self.get_headers()
            headers['Host'] = 'www.flipkart.com'
            
            response = self.session.get(search_url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Start from all anchors; we'll filter by URL pattern so it works across categories
            product_cards = soup.find_all('a', href=True)
            
            seen_urls = set()
            for link in product_cards:
                href = link.get('href', '')
                # Accept typical Flipkart product URLs for any category
                if ('/p/' not in href and '/product/' not in href and 'pid=' not in href):
                    continue
                if href.startswith('/'):
                    url = 'https://www.flipkart.com' + href
                else:
                    # Some links may be protocol-relative or missing domain
                    if href.startswith('http'): 
                        url = href
                    else:
                        url = 'https://www.flipkart.com' + href
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                name = link.get('title') or link.get_text(strip=True)
                name = name[:200] if name else None
                
                # Try to find price near this link
                price_text = None
                parent = link.parent
                for _ in range(4):  # climb a few levels
                    if not parent:
                        break
                    price_div = parent.find('div', class_=re.compile(r'Nx9bqj|_30jeq3|_16Jk6d'))
                    if price_div and price_div.get_text(strip=True):
                        price_text = price_div.get_text(strip=True)
                        break
                    parent = parent.parent
                price = self.extract_price(price_text) if price_text else None
                
                # Try image
                image = None
                parent = link.parent
                for _ in range(4):
                    if not parent:
                        break
                    img = parent.find('img')
                    if img and img.get('src'):
                        image = img['src']
                        break
                    parent = parent.parent
                
                results.append({
                    'name': name,
                    'price': price,
                    'original_price': None,  # not trivial to extract from listing
                    'image': image,
                    'url': url,
                    'success': bool(name or price)
                })
                if len(results) >= max_results:
                    break
        except Exception as e:
            print(f"Flipkart multi-search error: {e}")
        
        # Filter out completely empty entries
        return [r for r in results if r.get('success')]

    def search_amazon_products(self, product_name, max_results=24):
        """Search Amazon by name and return a list of lightweight product dicts.

        Parses the search results listing instead of scraping each product page.
        """
        search_query = quote_plus(' '.join(product_name.split()[:5]))
        search_url = f"https://www.amazon.in/s?k={search_query}"
        results = []
        
        try:
            print(f"Searching Amazon for multiple products: {product_name[:50]}...")
            headers = self.get_headers()
            headers['Host'] = 'www.amazon.in'
            
            response = self.session.get(search_url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Each search result is usually in a div.s-result-item
            cards = soup.find_all('div', {'data-component-type': 's-search-result'})
            seen_urls = set()
            for card in cards:
                link = card.find('a', href=True, class_=re.compile(r'a-link-normal'))
                if not link:
                    continue
                href = link.get('href', '')
                if '/dp/' not in href and '/gp/product/' not in href:
                    continue
                if href.startswith('/'):
                    url = 'https://www.amazon.in' + href
                else:
                    url = href
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # Title
                title_span = card.find('span', class_=re.compile(r'a-size-medium|a-size-base-plus'))
                name = title_span.get_text(strip=True)[:200] if title_span else None
                
                # Price
                price_span = card.find('span', class_=re.compile(r'a-price-whole'))
                if not price_span:
                    price_span = card.find('span', class_=re.compile(r'a-offscreen'))
                price_text = price_span.get_text(strip=True) if price_span else None
                price = self.extract_price(price_text) if price_text else None
                
                # Image
                img = card.find('img')
                image = img.get('src') if img and img.get('src') else None
                
                results.append({
                    'name': name,
                    'price': price,
                    'original_price': None,
                    'image': image,
                    'url': url,
                    'success': bool(name or price)
                })
                if len(results) >= max_results:
                    break
        except Exception as e:
            print(f"Amazon multi-search error: {e}")
        
        return [r for r in results if r.get('success')]


def generate_mock_price_history(product_id, amazon_price, flipkart_price, days=90):
    import random
    from datetime import datetime, timedelta
    
    history = []
    base_amazon = amazon_price if amazon_price else 0
    base_flipkart = flipkart_price if flipkart_price else 0
    
    for i in range(days):
        date = datetime.utcnow() - timedelta(days=days - i)
        
        amazon_variation = random.uniform(-0.15, 0.15)
        flipkart_variation = random.uniform(-0.15, 0.15)
        
        history.append({
            'date': date.strftime('%Y-%m-%d'),
            'amazon_price': round(base_amazon * (1 + amazon_variation), 2) if base_amazon else None,
            'flipkart_price': round(base_flipkart * (1 + flipkart_variation), 2) if base_flipkart else None
        })
    
    return history
