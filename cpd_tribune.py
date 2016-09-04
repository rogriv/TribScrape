__author__ = 'romar9393'

from bs4 import BeautifulSoup
import pandas as pd
import urllib.request
import pickle
from string import punctuation
from wordcloud import WordCloud
import re
import string
from collections import Counter

base_search_url = 'http://www.chicagotribune.com/search/dispatcher.front?page='
end_search_url = '&target=stories&spell=on&Query=chicago%20police%20department#trb_search'
base_url = 'http://www.chicagotribune.com'

# collect all page urls from the tribune search for "chicago police department"
# return list of urls
def collect_page_urls(bsu, esu):
    urls = []
    page_not_found = False
    i = 1
    while page_not_found == False:
        url = bsu + str(i) + esu
        htmlText = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(htmlText)

        div = soup.find('div', attrs = {'class': 'trb_searchresults'})
        try:
            links = div.findAll('a', attrs = {'class' : 'trb_search_result_title'})
            links = [link.get('href') for link in links]
            urls = urls + links
            i +=1
        except:
            page_not_found = True
    print(len(urls))
    return(urls)


#pickle.dump(collect_page_urls(base_search_url, end_search_url), open("url_list.pickle", 'wb'))
#url_list = pickle.load(open('url_list.pickle', 'rb'))

# scrape an individual url's page
# return the text, date, and url
def scrape_page(url):
    url = base_url + url
    htmlText = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(htmlText)
    date = soup.find('div', {'class' : 'trb_ar_dateline'}).find('time')['datetime']
    texts = soup.findAll('p')[:-1]
    texts = [text.getText() for text in texts]
    text = " ".join(texts)
    return([date, url, text])


# construct a dataframe with columns date, url, and words
# return dataframe where a row is a article/url
def make_text_dataframe(urls):
    df = pd.DataFrame(columns= ['date', 'url', 'words'])
    for url in urls:
        try:
            df.loc[len(df)] = scrape_page(url)
        except:
            df.loc[len(df)] = ['error', url,'error']
    return(df)

#make_text_dataframe(collect_page_urls(base_search_url, end_search_url)).to_csv('trib_cpd_text.csv')

# filters through dataframe of article text to format text
# and determine if article contains the correct phrases
# return formatted dataframe
def find_suitable_articles(df):
    drop_list = []
    for i, row in df.iterrows():
        words = row['words']
        if type(words) != str:
            drop_list.append(i)
    df = df.drop(df.index[drop_list])
    drop_list = []
    df = df[df['date'] != 'error']
    df = df.dropna(how='any').reset_index(drop=True)
    df['words'] = df['words'].apply(lambda x: re.sub('['+string.punctuation+']', ' ', re.sub('<[^<]+?>', '', x)).lower())
    for i, row in df.iterrows():
        words = row['words']
        if not (words.find('chicago police') > -1 or words.find('fraternal order') > -1 or words.find('police union') > -1):
                drop_list.append(i)
    df = df.drop(df.index[drop_list])
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].apply(lambda x: x.year)
    #df = df[df['year'] >= 2007]
    df = df.dropna(how='any').reset_index(drop=True)
    return(df)

# creates word cloud by year of article publishing
# removes undesirable words like the top 200 most common english words
# and other specified undesirable words
# creates word clouds and saves them
# with file path = 'trib_wordcloud[year]_[number of used articles].png'
def make_wordcloud_by_year(df):
    z = df.groupby(['year'])['words'].apply(lambda x: re.sub('['+string.punctuation+']', ' ', re.sub('<[^<]+?>', '', ' '.join(x))).lower())
    f = open('google-10000-english-usa.txt', 'r').readlines()
    f = [i.replace('\n', '') for i in f]
    f = f[0:199]
    f = f + ['chicago', 'police', 'department', 'officer', 'officers', 'tribune', 'avenue', 'block', 'district', 'call', 'park', 'cook', 'man', 'old', 'say', 'around', 'woman', 'street', 'found', 'someone']
    for i in range(len(z)):
        narticles = len(df[df['year'] == z.index[i]])
        t = z[z.index[i]]
        t = ' '.join([word for word in t.split() if word not in f])
        wordcloud = WordCloud(max_font_size= 40, relative_scaling= 0.5).generate(t)
        wordcloud.to_file('trib_wordcloud'+str(z.index[i]) + '_' + str(narticles) + '.png')

# creates word count dataframe
# creates word count percentage dataframe
# deletes 200 most common english words
# returns dataframe with columns = year, rows = word
# cells = total count [or density] of word in all articles that year
# saves dataframes as 'word_dataframe.csv' and 'word_dateframe_pc.csv'
def make_word_count_by_year_dataframe(df):
    z = df.groupby(['year'])['words'].apply(lambda x: re.sub('['+string.punctuation+']', ' ', re.sub('<[^<]+?>', '', ' '.join(x))).lower())
    f = open('google-10000-english-usa.txt', 'r').readlines()
    f = [i.replace('\n', '') for i in f]
    f = f[0:199]
    big_dict = {}
    all_words = []
    for i in range(len(z)):
        narticles = len(df[df['year'] == z.index[i]])
        t = z[z.index[i]]
        t = [word for word in t.split() if word not in f]
        dict = Counter(t)
        big_dict[str(z.index[i])] = {'narticles' : narticles, 'word_counts' : dict, 'total_words' : sum(dict.values())}
        all_words  = all_words + list(dict.keys())
    all_words = list(Counter(all_words).keys())
    word_df = pd.DataFrame(columns= [str(i) for i in pd.unique(df['year'])], index = all_words)
    for y, d in big_dict.items():
        for w, c in d['word_counts'].items():
            word_df.set_value(w, y, c)
    word_df_pc = pd.DataFrame(columns= [str(i) for i in pd.unique(df['year'])], index = all_words)
    for y, d in big_dict.items():
        for w, c in d['word_counts'].items():
            word_df_pc.set_value(w, y, c/d['total_words'])
    word_df_pc.fillna(0).to_csv('word_dateframe_pc.csv')
    word_df.fillna(0).to_csv('word_dataframe.csv')

#find_suitable_articles_to_wordcloud(make_text_dataframe(collect_page_urls(base_search_url, end_search_url)))
df = find_suitable_articles(pd.read_csv('trib_cpd_text.csv'))
#make_word_count_by_year_dataframe(df)
make_wordcloud_by_year(df)

