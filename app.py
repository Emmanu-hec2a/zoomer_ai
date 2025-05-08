from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import datetime
import os
from dotenv import load_dotenv
import numpy as np
import faiss
import time
import backoff

app = Flask(__name__)
load_dotenv()

# Initialize NetMind API
client = OpenAI(
    base_url="https://api.netmind.ai/inference-api/openai/v1",
    api_key=os.getenv("OPEN_API_KEY")
)

# Directly define your FAQ data
faqs_data = {
    "title": "CenterHelp/Frequently Asked Questions(FAQs)",
    "introduction": "Welcome to the Zoomer Africa Help Center!\nHere you'll find answers to common questions about our platform. If you can't find what you're looking for, please don't hesitate to contact our support team.",
    "sections": [
        {
            "title": "Getting Started",
            "questions": [
                {
                    "q": "How do I sign up for Zoomer Africa?",
                    "a": "You can sign up by clicking the \"Sign Up\" button on our homepage or mobile app. You'll need to provide your name, email address, and create a password. You may also have the option to sign up using your existing Google account."
                },
                {
                    "q": "Is Zoomer Africa free to use?",
                    "a": "Yes, Zoomer Africa is free to sign up and use for basic features like connecting with friends, sharing updates, and joining communities. We have optional premium features or services for users who want to use the platform to its full potential."
                },
                {
                    "q": "I'm having trouble signing up. What should I do?",
                    "a": "Please double-check that you've entered your email address correctly and that your password meets the requirements. If you're still experiencing issues, please contact our support team through the \"Contact Us\" page with a description of the problem."
                }
            ]
        },
        {
            "title": "Your Profile in Default Mode",
            "questions": [
                {
                    "q": "How do I edit my profile?",
                    "a": "Once you're logged in, navigate to your profile page by clicking on your profile picture under “Menu” in the bottom right corner. Click Settings. On the top left corner, near the Zoomer logo, tap the Menu icon (three horizontal lines) to access the edit features. You should find an \"Edit Profile\" option that allows you to update your information."
                },
                {
                    "q": "How can I change my password?",
                    "a": "Go to your account settings after Clicking under a dropdown menu in the right Corner associated with your profile.Click Settings,On the three horizontal lines near the zoomer logo in the upper top left,Tap Security settings for a \"Change Password\" option and follow the instructions."
                },
                {
                    "q": "How do I control who sees my posts?",
                    "a": "When you create a new post, you'll typically have options to adjust the privacy settings. You can usually choose to share your post with everyone, only your friends/connections, or specific groups."
                }
            ]
        },
        {
            "title": "Connecting with Others",
            "questions": [
                {
                    "q": "How do I find and connect with friends?",
                    "a": "You can search for other users by their name or username using the search bar. You can also explore suggested connections based on your profile and interests. To connect, simply click the \"Follow\" button on their profile."
                },
                {
                    "q": "How do I create or join a community?",
                    "a": "Look for \"Communities\" or \"Groups\" section on the platform by clicking home,On the top left Corner, Click the three horizontal lines,You should find options to create your own group(community) or browse existing ones based on your interests."
                }
            ]
        },
        {
            "title": "Using Zoomer Africa",
            "questions": [
                {
                    "q": "How do I post?",
                    "a": "To share a post on feeds or timeline(share to group and page), look for the  \"Post,\" button in-between the “reels” and “search” buttons below the website page or a similar button on timeline. Click it, type your message, and you'll have options to add photos, videos, links,files,albums,voice notes,etc,choose your audience before clicking \"Post.\""
                },
                {
                    "q": "How do I like, comment on, and share posts?",
                    "a": "Below each post, you'll find interactive icons. Tap the heart(faceups emogis) or thumbs-up icon to \"like\" a post, click the speech bubble icon to add a \"comment,\" and tap the arrow icon to \"share\" the post with your friends or other platforms."
                },
                {
                    "q": "How do I save posts?",
                    "a": "You should see a \"Save\" icon ( a bookmark) on posts just In Front of your profile name with an arrow facing down. Tapping this will bring you the “save”  option and add the post to a private \"Saved section\" or collection that you can access later from your account."
                },
                {
                    "q": "How do I view my memories?",
                    "a": "Look for  \"Memories\" just below the saved posts on feeds menu section in your account. This will show you past posts and activities from previous years."
                }
            ]
        },
        {
            "title": "Theme Switcher",
            "questions": [
                {
                    "q": "Does Zoomer Africa have a dark mode or different themes?",
                    "a": "Yes, you can customize your viewing experience with our theme switcher accessed through clicking down on the Menu Profile in the right bottom corner. You'll typically find this option in your account settings after scrolling down to allow you to switch between light and dark modes or choose from default to elengine."
                }
            ]
        },
        {
            "title": "Points System",
            "questions": [
                {
                    "q": "What is the points system?",
                    "a": "Zoomer Africa rewards active participation! You can earn points for various activities like liking posts, leaving thoughtful comments, posting your own blogs, photos, and videos, and more.Each 100 points is equivalent to 1 UGX. Your daily points limit is 50,000 points, and you currently have 50,000 remaining points. Your daily limit will reset after 24 hours from your last valid earned action. You can choose to withdraw your earnings or transfer them to your wallet."
                },
                {
                    "q": "How do I earn points?",
                    "a": "Points are automatically credited to your account when you perform eligible actions i.e viewing and liking posts,commenting on,sharing the platform through your affiliate link,creating posts and blogs,The number of points awarded may vary depending on the activity,for example:\n5 points for creating a new post.\n0.1 points for each post view.\n6 points for any reaction on your post.\n5 points for commenting on any post.\n5 points for reacting on any posts.\n5 points for each follower you get/got.\n5 points for referring a user."
                },
                {
                    "q": "What can I do with my points?",
                    "a": "Accumulated points may unlock various benefits, such as increased visibility for your content, access to exclusive features(upgrades), the ability to boost your posts, or even redeem them for virtual rewards or discounts within the platform. Visit our \"Points & Rewards\" page for more information."
                }
            ]
        },
        {
            "title": "Verification",
            "questions": [
                {
                    "q": "What is account verification?",
                    "a": "Account verification adds a visible badge (a blue checkmark) to profiles and pages to confirm their authenticity. This helps users identify genuine accounts of public figures, brands, and organizations."
                },
                {
                    "q": "How can I get my account verified?",
                    "a": "Our verification process typically involves submitting a National I'd card,Passport or Driver's licence  with proof of identity and demonstrating public interest or relevance.Please visit our \"Verification\" page for detailed criteria and the application process."
                }
            ]
        },
        {
            "title": "Security Settings",
            "questions": [
                {
                    "q": "What security settings are available?",
                    "a": "We offer several security features to protect your account, including password management, two-factor authentication (2FA) for added login security, and the ability to review and manage logged-in sessions. You can find these options in your account's security settings by tapping on the menu profile button below the right bottom corner,click settings then the three horizontal lines in the top right corner,you should find the security settings option to edit password and 2 factor authentication."
                },
                {
                    "q": "How do I enable two-factor authentication?",
                    "a": "In your security settings, you'll find the option to enable 2FA. You'll typically need to link your phone number or use an authenticator app to generate verification codes when you log in from a new device."
                }
            ]
        },
        {
            "title": "Privacy",
            "questions": [
                {
                    "q": "What are my privacy options or Privacy?",
                    "a": "We provide granular privacy controls that allow you to manage who can see your profile information, posts, friend lists, and more. You can adjust these settings in the \"Privacy\" section of your account settings."
                },
                {
                    "q": "How can I control who can message me,poke me,send me gifts,post on your wall,see my agender,birthday,work place info,location,education info,other info, followers/followings,subscription,photos,liked pages,joined groups and events?",
                    "a": "In your privacy settings, you can edit all the above according to your wish."
                }
            ]
        },
        {
            "title": "Blocking",
            "questions": [
                {
                    "q": "How do I block someone?",
                    "a": "If you want to prevent someone from seeing your profile or contacting you, you can block them. You'll find a \"Block\" option on their profile  ,click the three dots In Front of message book,You should see a blocking option when you scroll down."
                },
                {
                    "q": "What happens when I block someone?",
                    "a": "When you block someone, they will no longer be able to see your posts, view your profile, send you messages, or interact with you on the platform. They will also be removed from your friends/followers list, and you will be removed from theirs."
                }
            ]
        },
        {
            "title": "Connecting  and Linking Accounts to your Zoomer Account.",
            "questions": [
                {
                    "q": "How can I connect other social media accounts to my account?",
                    "a": "In your account settings,Under the Menu profile,Click settings,On the three horizontal lines in the upper left corner,Edit profile.you should find an option to link your accounts on other platforms like Twitter, Instagram, or Facebook under social links."
                }
            ]
        },
        {
            "title": "Membership Subscription",
            "questions": [
                {
                    "q": "Does Zoomer Africa offer a membership program?",
                    "a": "Yes,We offer a formal membership program, but to only verified accounts who want to upgrade to use Zoomer Africa to its full potential.For Example:\na).Pay Ush 50,000 to get Bronze Package for one month(featured member,no ads,verified badge,boost up to 5 posts,boost upto 2 pages,all permissions)\nb).Pay Ush 90,000 to get Silver Package for One month(featured member,no ads,verified badge,boost upto 10 posts,boost upto 5 pages,all permissions)\nc).Pay Ush 150,000 to get Gold Package for one month(featured member,no ads,verified badge,boost upto 10 posts,boost upto 10 pages,all permissions)\nd).Pay Ush 500,000 to get Platinum package for lifetime(featured member,no ads,verified badge,boost upto 100 posts,boost upto 100 pages,all permissions)"
                },
                {
                    "q": "How do I become membership?",
                    "a": "sign up on Zoomer Africa for free and upgrade for the membership subscription by verifying your account first."
                }
            ]
        },
        {
            "title": "Monetisation and Commission.",
            "questions": [
                {
                    "q": "Can I earn money on Zoomer Africa?",
                    "a": "Yes, we offer various ways for creators to potentially monetize their content and engagement on the platform. These may include for example:\nad revenue sharing, tips, subscriptions, selling content(paid posts,chats,audio/video calls.Visit our \"Monetisation\" page for details and eligibility criteria under menu profile.\nA 5% of commission will be deducted from each user for Monetisation to cater for the Zoomer Africa Operations and modifications."
                },
                {
                    "q": "How does monetisation work?",
                    "a": "Monetization converts online presence into revenue through methods like:\n-Advertising\n-Sponsored content\n-Affiliate marketing\n-Selling products/services\n-Subscription-based models\nThat is to say,each user is able to earn money through their content as stated above."
                }
            ]
        },
        {
            "title": "Affiliates",
            "questions": [
                {
                    "q": "Does Zoomer Africa have an affiliate program?",
                    "a": "Yes, our affiliate program allows you to earn commissions by referring new users.Earn 5 points/5ugsh for each user you refer and registers under your referral link."
                }
            ]
        },
        {
            "title": "Marketplace",
            "questions": [
                {
                    "q": "What is the Marketplace?",
                    "a": "Our Marketplace is a space where users and businesses can buy and sell goods and services within the Zoomer Africa community. You can browse listings, connect with sellers, and discover unique offerings."
                },
                {
                    "q": "How do I buy and sell on the Marketplace?",
                    "a": "To buy, navigate to the \"Marketplace\" section and browse listings. To sell, you'll typically need to set up a seller profile and follow the instructions for creating listings."
                }
            ]
        },
        {
            "title": "Your Addresses",
            "questions": [
                {
                    "q": "Why can I add my address?",
                    "a": "Adding your address can be useful for various features, such as connecting with local communities, participating in location-based events, or facilitating transactions within the Marketplace. You can manage your address information in your profile settings."
                },
                {
                    "q": "Is my address information private?",
                    "a": "You have control over the visibility of your address information in your privacy settings. You can choose who can see it, such as only yourself, your friends, or no one."
                }
            ]
        },
        {
            "title": "Your Information",
            "questions": [
                {
                    "q": "What personal information does Zoomer Africa collect?",
                    "a": "We collect information that you provide when you sign up and use the platform, such as your name, email address, profile information, and content you share. We also collect certain usage data to improve our services. Please refer to our Privacy Policy for a detailed explanation."
                },
                {
                    "q": "How is my personal information used?",
                    "a": "Your personal information is used to provide and improve our services, personalize your experience, connect you with others, and communicate with you. We do not share your personal information with third parties for their marketing purposes without your consent. Please review our Privacy Policy for more details."
                }
            ]
        },
        {
            "title": "Creating Ads",
            "questions": [
                {
                    "q": "Can I create ads on Zoomer Africa?",
                    "a": "Yes, businesses and individuals can create ads to reach a wider audience on our platform. Our ad platform allows you to target specific demographics and interests. Visit our \"Advertise\" page to learn more about creating and managing ads."
                },
                {
                    "q": "How do I create an ad campaign?",
                    "a": "On Home page,Click on the three lines in the upper left corner,scroll down for  \"Ads manager\" option and create new campaign. you'll find tools and guides to help you set up your ad campaign, define your target audience, set your budget, and design your ad creatives."
                }
            ]
        },
        {
            "title": "Products",
            "questions": [
                {
                    "q": "What are \"Products\" on Zoomer Africa?",
                    "a": "The \"Products\" feature allows businesses and creators to showcase and sell their goods directly to the Zoomer Africa community. You can browse product listings, view details, and make purchases within the platform."
                },
                {
                    "q": "How do I list my products for sale?",
                    "a": "If you have a business profile, you'll typically find an option to add and manage your products in your profile settings or \"Products\" section."
                }
            ]
        },
        {
            "title": "Fund Raising",
            "questions": [
                {
                    "q": "Can I raise funds for a project or cause on Zoomer Africa?",
                    "a": "Yes, we offer tools and features that allow individuals and organizations to create fundraising
