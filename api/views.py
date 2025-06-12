import os
import requests
import locale
import logging
from json import JSONDecodeError
import cloudscraper

from django.http import HttpResponse
from .images import UNKNOWN, UNRATED, BRONZE, SILVER, GOLD, PLATINUM, DIAMOND, RUBY, MASTER

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

logger = logging.getLogger('testlogger')

# Create your views here.
TIERS = (
    "Unrated",
    "Bronze 5", "Bronze 4", "Bronze 3", "Bronze 2", "Bronze 1",
    "Silver 5", "Silver 4", "Silver 3", "Silver 2", "Silver 1",
    "Gold 5", "Gold 4", "Gold 3", "Gold 2", "Gold 1",
    "Platinum 5", "Platinum 4", "Platinum 3", "Platinum 2", "Platinum 1",
    "Diamond 5", "Diamond 4", "Diamond 3", "Diamond 2", "Diamond 1",
    "Ruby 5", "Ruby 4", "Ruby 3", "Ruby 2", "Ruby 1",
    "Master"
)

BACKGROUND_COLOR = {
    'Unknown': ['#AAAAAA', '#666666', '#000000'],
    'Unrated': ['#666666', '#2D2D2D', '#040202'],
    'Bronze': ['#F49347', '#984400', '#492000'],
    'Silver': ['#939195', '#6B7E91', '#1F354A'],
    'Gold': ['#FFC944', '#FFAF44', '#FF9632'],
    'Platinum': ['#8CC584', '#45B2D3', '#51A795'],
    'Diamond': ['#96B8DC', '#3EA5DB', '#4D6399', ],
    'Ruby': ['#E45B62', '#E14476', '#CA0059'],
    'Master': ['#83f8fe', '#b297fc', '#fc7ea8'],
}

BACKGROUND_COLOR_PASTEL = {
    'Unknown': ['#eeeeee', '#dadada'],
    'Unrated': ['#dddddd', '#aaaaaa'],
    'Bronze': ['rgb(197, 164, 143)', 'rgb(222, 176, 132)'],
    'Silver': ['rgb(225, 204, 204)', 'rgb(182, 178, 177)'],
    'Gold': ['rgb(265, 237, 150)', 'rgb(255, 190, 138)'],
    'Platinum': ['rgb(180, 247, 249)', 'rgb(200, 260, 218)'],
    'Diamond': ['rgb(195, 236, 249)', 'rgb(187, 202, 250)'],
    'Ruby': ['rgb(253, 205, 185)', 'rgb(255, 130, 155)'],
    'Master': ['rgb(196, 254, 255)', 'rgb(255, 210, 234)'],
}

TIER_IMG_LINK = {
    'Unknown': UNKNOWN,
    'Unrated': UNRATED,
    'Bronze': BRONZE,
    'Silver': SILVER,
    'Gold': GOLD,
    'Platinum': PLATINUM,
    'Diamond': DIAMOND,
    'Ruby': RUBY,
    'Master': MASTER
}

TIER_RATES = (
    0, # unranked
    30, 60, 90, 120, 150, # bronze
    200, 300, 400, 500, 650, # silver
    800, 950, 1100, 1250, 1400, # gold
    1600, 1750, 1900, 2000, 2100, # platinum
    2200, 2300, 2400, 2500, 2600, # diamond
    2700, 2800, 2850, 2900, 2950, # ruby
    3000 # master
)

class UrlSettings(object):
    def __init__(self, request, MAX_LEN):
        self.api_server = 'https://solved.ac/api'
        self.boj_handle = request.GET.get("boj", "ccoco")
        if len(self.boj_handle) > MAX_LEN:
            self.boj_name = self.boj_handle[:(MAX_LEN - 2)] + "..."
        else:
            self.boj_name = self.boj_handle
        self.user_information_url = self.api_server + \
            '/v3/user/show?handle=' + self.boj_handle


class BojDefaultSettings(object):
    def __init__(self, request, url_set):
        try:
            # self.json = requests.get(url_set.user_information_url).json()
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url_set.user_information_url)
            if resp.status_code != 200:
                logger.error(f"API request failed: {resp.status_code} {resp.text}")
                raise JSONDecodeError("Non-200 response", resp.text, 0)
            self.json = resp.json()
            self.rating = self.json['rating']
            self.level = self.boj_rating_to_lv(self.json['rating'])
            self.solved = '{0:n}'.format(self.json['solvedCount'])
            self.boj_class = self.json['class']
            self.boj_class_decoration = ''
            if self.json['classDecoration'] == 'silver':
                self.boj_class_decoration = '+'
            elif self.json['classDecoration'] == 'gold':
                self.boj_class_decoration = '++'

            self.my_rate = self.json['rating']
            if self.level == 31:
                self.prev_rate = TIER_RATES[self.level]
                self.next_rate = TIER_RATES[self.level]
                self.percentage = 100
            else:
                self.prev_rate = TIER_RATES[self.level]
                self.next_rate = TIER_RATES[self.level+1]
                self.percentage = round(
                    (self.my_rate - self.prev_rate) * 100 / (self.next_rate - self.prev_rate))
            self.bar_size = 35 + 2.55 * self.percentage

            self.needed_rate = '{0:n}'.format(self.next_rate)
            self.now_rate = '{0:n}'.format(self.my_rate)
            self.rate = '{0:n}'.format(self.my_rate)

            if TIERS[self.level] == 'Unrated' or TIERS[self.level] == 'Master':
                self.tier_title = TIERS[self.level]
                self.tier_rank = ''
            else:
                self.tier_title, self.tier_rank = TIERS[self.level].split()
        except JSONDecodeError as e:
            logger.error(e)
            self.tier_title = "Unknown"
            url_set.boj_handle = 'Unknown'
            self.tier_rank = ''
            self.solved = '0'
            self.boj_class = '0'
            self.boj_class_decoration = ''
            self.rate = '0'
            self.now_rate = '0'
            self.needed_rate = '0'
            self.percentage = '0'
            self.bar_size = '35'

    def boj_rating_to_lv(self, rating):
        if rating < 30: return 0
        if rating < 150: return rating // 30
        if rating < 200: return 5
        if rating < 500: return (rating-200) // 100 + 6
        if rating < 1400: return (rating-500) // 150 + 9
        if rating < 1600: return 15
        if rating < 1750: return 16
        if rating < 1900: return 17
        if rating < 2800: return (rating-1900) // 100 + 18
        if rating < 3000: return (rating-2800) // 50 + 27
        return 31


def generate_badge(request):
    MAX_LEN = 11
    url_set = UrlSettings(request, MAX_LEN)
    handle_set = BojDefaultSettings(request, url_set)
    svg = '''
    <!DOCTYPE svg PUBLIC
        "-//W3C//DTD SVG 1.1//EN"
        "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg height="170" width="350"
    version="1.1"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xml:space="preserve">
    <style type="text/css">
        <![CDATA[
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=block');
            @keyframes delayFadeIn {{
                0%{{
                    opacity:0
                }}
                60%{{
                    opacity:0
                }}
                100%{{
                    opacity:1
                }}
            }}
            @keyframes fadeIn {{
                from {{
                    opacity: 0;
                }}
                to {{
                    opacity: 1;
                }}
            }}
            @keyframes rateBarAnimation {{
                0% {{
                    stroke-dashoffset: {bar_size};
                }}
                70% {{
                    stroke-dashoffset: {bar_size};
                }}
                100%{{
                    stroke-dashoffset: 35;
                }}
            }}
            .background {{
                fill: url(#grad);
            }}
            text {{
                fill: white;
                font-family: 'Noto Sans KR', sans-serif;
            }}
            text.boj-handle {{
                font-weight: 700;
                font-size: 1.45em;
                animation: fadeIn 0.8s ease-in-out forwards;
            }}
            text.tier-text {{
                font-weight: 700;
                font-size: 1.45em;
                opacity: 55%;
            }}
            text.tier-number {{
                font-size: 3.1em;
                font-weight: 700;
            }}
            .subtitle {{
                font-weight: 500;
                font-size: 0.9em;
            }}
            .value {{
                font-weight: 400;
                font-size: 0.9em;
            }}
            .percentage {{
                font-weight: 300;
                font-size: 0.8em;
            }}
            .progress {{
                font-size: 0.7em;
            }}
            .item {{
                opacity: 0;
                animation: delayFadeIn 1s ease-in-out forwards;
            }}
            .rate-bar {{
                stroke-dasharray: {bar_size};
                stroke-dashoffset: {bar_size};
                animation: rateBarAnimation 1.5s forwards ease-in-out;
            }}
        ]]>
    </style>
    <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="35%">
            <stop offset="10%" style="stop-color:{color1};stop-opacity:1"></stop>
            <stop offset="55%" style="stop-color:{color2};stop-opacity:1"></stop>
            <stop offset="100%" style="stop-color:{color3};stop-opacity:1"></stop>
        </linearGradient>
    </defs>
    <rect width="350" height="170" rx="10" ry="10" class="background"/>
    <text x="315" y="50" class="tier-text" text-anchor="end" >{tier_title}{tier_rank}</text>
    <text x="35" y="50" class="boj-handle">{boj_handle}</text>
    <g class="item" style="animation-delay: 200ms">
        <text x="35" y="79" class="subtitle">rate</text><text x="145" y="79" class="rate value">{rate}</text>
    </g>
    <g class="item" style="animation-delay: 400ms">
        <text x="35" y="99" class="subtitle">solved</text><text x="145" y="99" class="solved value">{solved}</text>
    </g>
    <g class="item" style="animation-delay: 600ms">
        <text x="35" y="119" class="subtitle">class</text><text x="145" y="119" class="class value">{boj_class}{boj_class_decoration}</text>
    </g>
    <g class="rate-bar" style="animation-delay: 800ms">
        <line x1="35" y1="142" x2="{bar_size}" y2="142" stroke-width="4" stroke="floralwhite" stroke-linecap="round"/>
    </g>
    <line x1="35" y1="142" x2="290" y2="142" stroke-width="4" stroke-opacity="40%" stroke="floralwhite" stroke-linecap="round"/>
    <text x="297" y="142" alignment-baseline="middle" class="percentage">{percentage}%</text>
    <text x="293" y="157" class="progress" text-anchor="end">{now_rate} / {needed_rate}</text>
</svg>
    '''.format(color1=BACKGROUND_COLOR[handle_set.tier_title][0],
               color2=BACKGROUND_COLOR[handle_set.tier_title][1],
               color3=BACKGROUND_COLOR[handle_set.tier_title][2],
               boj_handle=url_set.boj_name,
               tier_rank=handle_set.tier_rank,
               tier_title=handle_set.tier_title,
               solved=handle_set.solved,
               boj_class=handle_set.boj_class,
               boj_class_decoration=handle_set.boj_class_decoration,
               rate=handle_set.rate,
               now_rate=handle_set.now_rate,
               needed_rate=handle_set.needed_rate,
               percentage=handle_set.percentage,
               bar_size=handle_set.bar_size)

    logger.info('[/generate_badge] user: {}, tier: {}'.format(url_set.boj_name, handle_set.tier_title))
    response = HttpResponse(content=svg)
    response['Content-Type'] = 'image/svg+xml'
    response['Cache-Control'] = 'max-age=3600'

    return response


def generate_badge_v2(request):
    MAX_LEN = 15
    url_set = UrlSettings(request, MAX_LEN)
    handle_set = BojDefaultSettings(request, url_set)
    svg = '''
    <!DOCTYPE svg PUBLIC
        "-//W3C//DTD SVG 1.1//EN"
        "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg height="170" width="350"
    version="1.1"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xml:space="preserve">
    <style type="text/css">
        <![CDATA[
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=block');
            @keyframes fadeIn {{
                0%{{
                    opacity:0
                }}
                100%{{
                    opacity:1
                }}
            }}
            @keyframes delayFadeIn {{
                0%{{
                    opacity:0
                }}
                80%{{
                    opacity:0
                }}
                100%{{
                    opacity:1
                }}
            }}
            @keyframes rateBarAnimation {{
                0% {{
                    stroke-dashoffset: {bar_size};
                }}
                70% {{
                    stroke-dashoffset: {bar_size};
                }}
                100%{{
                    stroke-dashoffset: 35;
                }}
            }}
            .background {{
                fill: url(#grad);
            }}
            text {{
                fill: white;
                font-family: 'Noto Sans KR', sans-serif;
            }}
            text.boj-handle {{
                font-weight: 700;
                font-size: 1.30em;
                animation: fadeIn 1s ease-in-out forwards;

            }}
            text.tier-text {{
                font-weight: 700;
                font-size: 1.45em;
                opacity: 55%;
            }}
            text.tier-number {{
                font-size: 3.1em;
                font-weight: 700;
                text-anchor: middle;
                animation: delayFadeIn 2s ease-in-out forwards;
            }}
            .subtitle {{
                font-weight: 500;
                font-size: 0.9em;
            }}
            .value {{
                font-weight: 400;
                font-size: 0.9em;
            }}
            .percentage {{
                font-weight: 300;
                font-size: 0.8em;
            }}
            .progress {{
                font-size: 0.7em;
            }}
            .item {{
                opacity: 0;
                animation: delayFadeIn 2s ease-in-out forwards;
            }}
            .rate-bar {{
                stroke-dasharray: {bar_size};
                stroke-dashoffset: {bar_size};
                animation: rateBarAnimation 1.5s forwards ease-in-out;
            }}
            .tier-title {{
                animation: delayFadeIn 2s ease-in-out forwards;
            }}
        ]]>
    </style>
    <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="35%">
            <stop offset="10%" style="stop-color:{color1};stop-opacity:1">
                <animate attributeName="stop-opacity" values="0.7; 0.73; 0.9 ; 0.97; 1; 0.97; 0.9; 0.73; 0.7;" dur="4s" repeatCount="indefinite" repeatDur="01:00"></animate>
            </stop>
            <stop offset="55%" style="stop-color:{color2};stop-opacity:1">
                <animate attributeName="stop-opacity" values="1; 0.95; 0.93; 0.95; 1;" dur="4s" repeatCount="indefinite" repeatDur="01:00"></animate>
            </stop>
            <stop offset="100%" style="stop-color:{color3};stop-opacity:1">
                <animate attributeName="stop-opacity" values="1; 0.97; 0.9; 0.83; 0.8; 0.83; 0.9; 0.97; 1;" dur="4s" repeatCount="indefinite" repeatDur="01:00"></animate>
            </stop>
        </linearGradient>
    </defs>
    <rect width="350" height="170" rx="10" ry="10" class="background"/>
    <line x1="34" y1="50" x2="34" y2="105" stroke-width="2" stroke="white">
        <animate attributeName="y2" dur="0.8s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.675 ; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="50 ; 50 ; 105" />
    </line>
    <line x1="34" y1="105" x2="67" y2="125" stroke-width="2" stroke="white">
        <animate attributeName="x2" dur="1s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.8 ; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="34 ; 34 ; 67" />
        <animate attributeName="y2" dur="1s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.8 ; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="105 ; 105 ; 125" />
    </line>
    <line x1="67" y1="125" x2="100" y2="105" stroke-width="2" stroke="white">
        <animate attributeName="x2" dur="1.2s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.83333 ; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="67 ; 67 ; 100" />
        <animate attributeName="y2" dur="1.2s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.83333 ; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="125 ; 125 ; 105" />
    </line>
    <line x1="100" y1="105" x2="100" y2="50" stroke-width="2" stroke="white">
        <animate attributeName="y2" dur="1.5s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.8 ; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="105 ; 105 ; 50" />
    </line>

    <line x1="67" y1="130" x2="34" y2="110" stroke-width="2" stroke="white">
        <animate attributeName="x2" dur="1.9s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.78947; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="67 ; 67 ; 34" />
        <animate attributeName="y2" dur="1.9s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.78947 ; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="130 ; 130 ; 110" />
    </line>

    <line x1="67" y1="130" x2="100" y2="110" stroke-width="2" stroke="white">
        <animate attributeName="x2" dur="1.9s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.78947 ; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="67 ; 67 ; 100" />
        <animate attributeName="y2" dur="1.9s" fill="freeze"
        calcMode="spline" keyTimes="0 ; 0.78947 ; 1"
        keySplines="0 0 1 1 ; 0.5 0 0.5 1" values="130 ; 130 ; 110" />
    </line>

    <text x="135" y="50" class="boj-handle">{boj_handle}</text>
    <image href="{tier_img_link}" x="18" y="12" height="50px" width="100px" class="tier-title"/>
    <text x="67" y="100" class="tier-number">{tier_rank}</text>
    <g class="item" style="animation-delay: 200ms">
        <text x="135" y="79" class="subtitle">rate</text><text x="225" y="79" class="rate value">{rate}</text>
    </g>
    <g class="item" style="animation-delay: 400ms">
        <text x="135" y="99" class="subtitle">solved</text><text x="225" y="99" class="solved value">{solved}</text>
    </g>
    <g class="item" style="animation-delay: 600ms">
        <text x="135" y="119" class="subtitle">class</text><text x="225" y="119" class="class value">{boj_class}{boj_class_decoration}</text>
    </g>
    <g class="rate-bar" style="animation-delay: 800ms">
        <line x1="35" y1="142" x2="{bar_size}" y2="142" stroke-width="4" stroke="floralwhite" stroke-linecap="round"/>
    </g>
    <line x1="35" y1="142" x2="290" y2="142" stroke-width="4" stroke-opacity="40%" stroke="floralwhite" stroke-linecap="round"/>
    <text x="297" y="142" alignment-baseline="middle" class="percentage">{percentage}%</text>
    <text x="293" y="157" class="progress" text-anchor="end">{now_rate} / {needed_rate}</text>
</svg>
    '''.format(color1=BACKGROUND_COLOR[handle_set.tier_title][0],
               color2=BACKGROUND_COLOR[handle_set.tier_title][1],
               color3=BACKGROUND_COLOR[handle_set.tier_title][2],
               boj_handle=url_set.boj_name,
               tier_rank=('M' if handle_set.tier_title == 'Master' else handle_set.tier_rank),
               tier_img_link=TIER_IMG_LINK[handle_set.tier_title],
               solved=handle_set.solved,
               boj_class=handle_set.boj_class,
               boj_class_decoration=handle_set.boj_class_decoration,
               rate=handle_set.rate,
               now_rate=handle_set.now_rate,
               needed_rate=handle_set.needed_rate,
               percentage=handle_set.percentage,
               bar_size=handle_set.bar_size)

    logger.info('[/generate_badge/v2] user: {}, tier: {}'.format(url_set.boj_name, handle_set.tier_title))
    response = HttpResponse(content=svg)
    response['Content-Type'] = 'image/svg+xml'
    response['Cache-Control'] = 'max-age=3600'

    return response

def generate_badge_mini(request):
    MAX_LEN = 11
    url_set = UrlSettings(request, MAX_LEN)
    handle_set = BojDefaultSettings(request, url_set)

    svg = '''
    <!DOCTYPE svg PUBLIC
        "-//W3C//DTD SVG 1.1//EN"
        "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg height="20" width="110"
    version="1.1"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xml:space="preserve">
    <style type="text/css">
        <![CDATA[
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=block');
            @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700&display=swap');
            @keyframes fadeIn {{
                from {{
                    opacity: 0;
                }}
                to {{
                    opacity: 1;
                }}
            }}
            @keyframes rateBarAnimation {{
                from {{
                    stroke-dashoffset: {bar_size};
                }}
                to {{
                    stroke-dashoffset: 35;
                }}
            }}
            .background {{
                fill: url(#grad1);
            }}
            text {{
                fill: white;
                font-family: 'Noto Sans KR', sans-serif;
                font-size: 0.7em;
            }}
            .gray-area {{
                fill: #555555;
            }}
            .tier {{
                font-weight: 700;
                font-size: 0.78em;
            }}
        ]]>
    </style>
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="35%">
            <stop offset="10%" style="stop-color:{color1};stop-opacity:1" />
            <stop offset="55%" style="stop-color:{color2};stop-opacity:1" />
            <stop offset="100%" style="stop-color:{color3};stop-opacity:1" />
        </linearGradient>
        <clipPath id="round-corner">
            <rect x="0" y="0" width="110" height="20" rx="3" ry="3"/>
        </clipPath>
    </defs>
    <rect width="40" height="20" x="70" y="0" rx="3" ry="3" class="background"/>
    <rect width="75" height="20" clip-path="url(#round-corner)" class="gray-area"/>
    <text text-anchor="middle" alignment-baseline="middle" dominant-baseline="middle" transform="translate(37.5, 11)">solved.ac</text>
    <text class="tier" text-anchor="middle" alignment-baseline="middle" dominant-baseline="middle" transform="translate(92, 11)">{tier_title}{tier_rank}</text>


</svg>
    '''.format(color1=BACKGROUND_COLOR[handle_set.tier_title][0],
               color2=BACKGROUND_COLOR[handle_set.tier_title][1],
               color3=BACKGROUND_COLOR[handle_set.tier_title][2],
               boj_handle=url_set.boj_name,
               tier_rank=handle_set.tier_rank,
               tier_title=handle_set.tier_title[0],
               solved=handle_set.solved,
               boj_class=handle_set.boj_class,
               rate=handle_set.rate,
               now_rate=handle_set.now_rate,
               needed_rate=handle_set.needed_rate,
               percentage=handle_set.percentage,
               bar_size=handle_set.bar_size)
    logger.info('[/generate_badge/mini ] user: {}, tier: {}'.format(url_set.boj_name, handle_set.tier_title))
    response = HttpResponse(content=svg)
    response['Content-Type'] = 'image/svg+xml'
    response['Cache-Control'] = 'max-age=86400'

    return response


def generate_badge_pastel(request):
    MAX_LEN = 11
    url_set = UrlSettings(request, MAX_LEN)
    handle_set = BojDefaultSettings(request, url_set)

    svg = '''
    <!DOCTYPE svg PUBLIC
        "-//W3C//DTD SVG 1.1//EN"
        "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg height="170" width="350"
    version="1.1"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xml:space="preserve">
    <style type="text/css">
        <![CDATA[
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=block');
            @keyframes delayFadeIn {{
                0%{{
                    opacity:0
                }}
                60%{{
                    opacity:0
                }}
                100%{{
                    opacity:1
                }}
            }}
            @keyframes fadeIn {{
                from {{
                    opacity: 0;
                }}
                to {{
                    opacity: 1;
                }}
            }}
            @keyframes rateBarAnimation {{
                0% {{
                    stroke-dashoffset: {bar_size};
                }}
                70% {{
                    stroke-dashoffset: {bar_size};
                }}
                100%{{
                    stroke-dashoffset: 35;
                }}
            }}
            .background {{
                fill: url(#grad);
            }}
            text {{
                fill: #555555;
                font-family: 'Noto Sans KR', sans-serif;
                opacity: 80%;
            }}
            text.boj-handle {{
                font-weight: 700;
                font-size: 1.45em;
                opacity: 75%;
                animation: fadeIn 0.8s ease-in-out forwards;
            }}
            text.tier-text {{
                font-weight: 700;
                font-size: 1.45em;
                opacity: 55%;
            }}
            text.tier-number {{
                font-size: 3.1em;
                font-weight: 700;
            }}
            .subtitle {{
                font-weight: 500;
                font-size: 0.9em;
            }}
            .value {{
                font-weight: 400;
                font-size: 0.9em;
            }}
            .percentage {{
                font-weight: 300;
                font-size: 0.8em;
            }}
            .progress {{
                font-size: 0.7em;
            }}
            .item {{
                opacity: 0;
                animation: delayFadeIn 1s ease-in-out forwards;
            }}
            .rate-bar {{
                stroke-dasharray: {bar_size};
                stroke-dashoffset: {bar_size};
                animation: rateBarAnimation 1.5s forwards ease-in-out;
            }}
        ]]>
    </style>
    <defs>
        <linearGradient id="linear-gradient" x1="0.066" y1="-0.15" x2="0.93" y2="0.925" gradientUnits="objectBoundingBox">
        <stop offset="0" stop-color="{color1}"/>
        <stop offset="1" stop-color="{color2}"/>
        </linearGradient>
    </defs>
    <rect id="사각형_2" data-name="사각형 2" width="350" height="170" rx="13" opacity="1" fill="url(#linear-gradient)"/>

    <text x="315" y="50" class="tier-text" text-anchor="end" >{tier_title}{tier_rank}</text>
    <text x="35" y="50" class="boj-handle">{boj_handle}</text>
    <g class="item" style="animation-delay: 200ms">
        <text x="35" y="79" class="subtitle">rate</text><text x="145" y="79" class="rate value">{rate}</text>
    </g>
    <g class="item" style="animation-delay: 400ms">
        <text x="35" y="99" class="subtitle">solved</text><text x="145" y="99" class="solved value">{solved}</text>
    </g>
    <g class="item" style="animation-delay: 600ms">
        <text x="35" y="119" class="subtitle">class</text><text x="145" y="119" class="class value">{boj_class}{boj_class_decoration}</text>
    </g>
    <line x1="35" y1="142" x2="290" y2="142" stroke-width="4" stroke-opacity="65%" stroke="floralwhite" stroke-linecap="round"/>
    <g class="rate-bar" style="animation-delay: 800ms">
        <line x1="35" y1="142" x2="{bar_size}" y2="142" stroke-width="4" stroke="#333333" stroke-linecap="round" stroke-opacity="60%"/>
    </g>
    <text x="297" y="142" alignment-baseline="middle" class="percentage">{percentage}%</text>
    <text x="293" y="157" class="progress" text-anchor="end">{now_rate} / {needed_rate}</text>
</svg>
    '''.format(color1=BACKGROUND_COLOR_PASTEL[handle_set.tier_title][0],
               color2=BACKGROUND_COLOR_PASTEL[handle_set.tier_title][1],
               boj_handle=url_set.boj_name,
               tier_rank=handle_set.tier_rank,
               tier_title=handle_set.tier_title,
               solved=handle_set.solved,
               boj_class=handle_set.boj_class,
               boj_class_decoration=handle_set.boj_class_decoration,
               rate=handle_set.rate,
               now_rate=handle_set.now_rate,
               needed_rate=handle_set.needed_rate,
               percentage=handle_set.percentage,
               bar_size=handle_set.bar_size)

    logger.info('[/generate_badge/pastel] user: {}, tier: {}'.format(url_set.boj_name, handle_set.tier_title))
    response = HttpResponse(content=svg)
    response['Content-Type'] = 'image/svg+xml'
    response['Cache-Control'] = 'max-age=3600'

    return response
