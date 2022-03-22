# Polyglot-Interlayer
Here are different versions of Interlayer for Polyglot
# Dependencies
For Google API - Python Client for Google Cloud Translation https://github.com/googleapis/python-translate, Apache-2.0 License
For Google Free API - Py-googletrans https://github.com/ssut/py-googletrans, MIT License
For Yandex API - not required
# Assembly Features
1. For building Google API with PyInstaller you need to use fix, described in this article: https://github.com/googleapis/google-cloud-python/issues/5774
2. For using Google Free API you should select version 4.0.0rc1 and don't update its dependencies after installation. The use of this version is strongly discouraged, it is unstable and does not translate correctly.
3. The Yandex API interlayer updates the token every hour, which can lead to bot freezes for a period of about five seconds during use.
