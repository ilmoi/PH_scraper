import csv

import bs4
import requests
import pprint
import re
import time
from selenium import webdriver



# ------------------------------------------------------------------------------
# use selenium to open the website -> find all commentators and makers urls
# have to use selenium, coz page is lazy loading and requests wont work

def scrape_project(url):
    # eg 'https://www.producthunt.com/posts/floyd-2'

    browser = webdriver.Chrome(executable_path='./chromeDriver/chromedriver')
    browser.get(url)

    time.sleep(3) #give it time to load

    hunter_and_makers_class = 'styles_makersContainer__1N77x'
    hunter_and_makers_raw = browser.find_elements_by_class_name(hunter_and_makers_class)

    commentators_and_likers = []
    hunter_and_makers = []

    # get everyone
    links = browser.find_elements_by_partial_link_text('')
    for l in links:
        href = l.get_attribute('href')
        if '@' in href and 'mailto' not in href:
            if href not in commentators_and_likers:
                commentators_and_likers.append(href)

    # get hunter and makers
    for hm in hunter_and_makers_raw:
        links = hm.find_elements_by_partial_link_text('')
        for l in links:
            href = l.get_attribute('href')
            if '@' in href and 'mailto' not in href:
                if href not in hunter_and_makers:
                    hunter_and_makers.append(href)

    #dedup
    commentators_and_likers = list(set(commentators_and_likers) - set(hunter_and_makers))

    print(f'COMMENTATORS / LIKERS: {len(commentators_and_likers)}')
    print(commentators_and_likers)
    print('...')
    print(f'HUNTER / MAKERS: {len(hunter_and_makers)}')
    print(hunter_and_makers)

    return commentators_and_likers, hunter_and_makers

# ------------------------------------------------------------------------------
# use bs4 to scrape the profile itself

def scrape_profile(profile_url, source_url, position):
    # eg 'https://www.producthunt.com/@lachlankirkwood'

    # fetch source
    res = requests.get(source_url)
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.text, 'lxml')
    source_title = soup.select('h1.styles_font__2Nqit.styles_xLarge__24CcJ.styles_headerPostName__a8Dcz.styles_lineHeight__2RYYy.styles_underline__20yPd')
    source_title = source_title[0].a.text
    print(source_title)

    # fetch profile
    res = requests.get(profile_url)
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.text, 'lxml')

    # twitter url
    twitter = ''
    links = soup.findAll('a') or []
    for link in links:
        href = link['href']
        if 'twitter' in href:
            twitter = href
    print(twitter)

    # name
    name = soup.select('.styles_font__2Nqit.styles_xLarge__24CcJ') or []
    if name:
        name = name[0].text
    else:
        name = ''
    print(name)

    # slogan
    slogan = soup.select('.styles_font__2Nqit.styles_medium__3fSwd.spacings_small__AQuIC') or []
    if slogan:
        slogan = slogan[0].text
    else:
        slogan = ''
    print(slogan)

    # topics
    topics = soup.select('.styles_font__2Nqit.styles_orange__3VieU.styles_small__2bw6M') or []
    topics = str([t.text.strip().strip(',') for t in topics]).replace("'","").replace('[', '').replace(']','')
    print(topics)

    # points
    points = soup.select('.styles_font__2Nqit.styles_grey__3J1TQ.styles_xSmall__1eYHj.styles_normal__iGf4Q.styles_text__3tT4S.styles_lineHeight__2RYYy.styles_underline__20yPd') or []
    if points:
        points = int(points[0].text.strip(' points').replace(',',''))
    else:
        points = ''
    print(points)

    #stats
    made, hunted, following, followers = 0, 0, 0, 0
    stats = made = soup.select('.styles_font__2Nqit.styles_small__2bw6M.styles_lineHeight__2RYYy.styles_underline__20yPd.styles_uppercase__2YIgd') or []
    for stat in stats:
        # stat = stat.text
        print(stat.text)
        print('-')
        if 'Made' in stat.text:
            made = int(stat.text.strip(' Made').replace(',', ''))
        elif 'Hunted'in stat.text:
            hunted = int(stat.text.strip(' Hunted').replace(',', ''))
        elif 'Following'in stat.text:
            following = int(stat.text.strip(' Following').replace(',', ''))
        elif 'Followers'in stat.text:
            followers = int(stat.text.strip(' Followers').replace(',', ''))

    #hack to fix made. When made not present a weird html element is pulled in. Here we replace it with 0
    try:
        made = int(made)
    except:
        made = 0

    print(made)
    print(hunted)
    print(following)
    print(followers)

    return [source_url, source_title, profile_url, position, twitter, name, slogan, topics, points, made, hunted, following, followers]


def append_csv(rows):
    with open('PH_scraped_data.csv', 'a') as f:
        csv_file = csv.writer(f)
        for row in rows:
            csv_file.writerow(row)


# ------------------------------------------------------------------------------
# bring it all together

# get project urls
with open('relevant_post_urls') as f:
    urls = f.readlines()

    # append the header row to csv (once)
    rows = [['source_url', 'source_title', 'profile_url', 'position', 'twitter', 'name', 'slogan', 'topics', 'points', 'made', 'hunted', 'following', 'followers']]
    append_csv(rows)

    # get profile urls
    for i, source_url in enumerate(urls):

        # reset rows
        rows = []

        source_url = source_url.strip('').strip(' ').strip('\n')
        print(f'================== [{i}/{len(urls)}] PROCESSING {source_url} ==================')
        commentators_and_likers, hunter_and_makers = scrape_project(source_url)
        hunter = hunter_and_makers[0]
        makers = hunter_and_makers[1:]

        # scrape profiles - 1)hunter
        try:
            row = scrape_profile(hunter, source_url, 'hunter')
            rows.append(row)
        except:
            pass

        # scrape profiles - 2)makers
        for profile in makers:
            try:
                row = scrape_profile(profile, source_url, 'maker')
                rows.append(row)
            except:
                pass

        # scrape profiles - 3)commentators & likers
        for profile in commentators_and_likers:
            try:
                row = scrape_profile(profile, source_url, 'commentator_liker')
                rows.append(row)
            except:
                pass

        # append to csv file afer a source is done
        append_csv(rows)
        print(f'================== [{i}/{len(urls)}] DONE ==================')