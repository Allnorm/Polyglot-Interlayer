import json
import logging
import sys
import time
import traceback

import requests


class Interlayer:
    class BadTrgLangException(Exception):
        pass

    class TooManyRequestException(Exception):
        pass

    class EqualLangsException(Exception):
        pass

    class BadSrcLangException(Exception):
        pass

    class TooLongMsg(Exception):
        pass

    class UnkTransException(Exception):
        pass

    class LangDetectException(Exception):
        pass

    class UnknownLang(Exception):
        pass

    class __TimeoutException(Exception):
        pass

    lang_list = {}
    iam_token = ""
    folder_id = ""
    oauth_token = ""
    headers = {}
    timer = 0
    __ATTEMPTS = 10

    def __get_response(self, url, request_json):
        for attempt in range(self.__ATTEMPTS + 1):

            if attempt == self.__ATTEMPTS:
                logging.error("Timeout exception!")
                raise self.__TimeoutException

            try:
                return requests.post(url, json=request_json, headers=self.headers, timeout=10)
            except requests.exceptions.Timeout:
                pass
            except Exception as e:
                logging.error(str(e) + "\n" + traceback.format_exc())
                raise self.__TimeoutException

    def init_dialog_api(self, config):

        self.folder_id, self.oauth_token = "", ""

        while self.folder_id == "":
            self.folder_id = input("Please, write your Folder ID: ")
        while self.oauth_token == "":
            self.oauth_token = input("Please, write your OAuth Token: ")

        config.add_section("Interlayer")
        config.set("Interlayer", "oauth-token", self.oauth_token)
        config.set("Interlayer", "folder-id", self.folder_id)
        return config

    def api_init(self, config):

        try:
            self.oauth_token = config["Interlayer"]["oauth-token"]
            self.folder_id = config["Interlayer"]["folder-id"]
        except KeyError:
            raise

        version = "1.3 for Yandex API (yapi)"
        build_date = "04.12.2022"
        version_polyglot = "1.4.4"
        logging.info("Interlayer version {} build date {}".format(version, build_date))
        logging.info("Compatible with version of Polyglot {}".format(version_polyglot))

        return config

    def translate_init(self):

        try:
            response = self.__get_response('https://iam.api.cloud.yandex.net/iam/v1/tokens',
                                           {"yandexPassportOauthToken": self.oauth_token})
        except self.__TimeoutException:
            logging.error("IAmToken wasn't updated successful! Bot will close!")
            sys.exit(1)

        if json.loads(response.text).get("message") is not None:
            logging.error("IAmToken wasn't updated successful! Bot will close!")
            logging.error(json.loads(response.text))
            sys.exit(1)

        self.iam_token = json.loads(response.text).get("iamToken")
        logging.info("IAmToken updated successfully")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {0}".format(self.iam_token)
        }

        self.timer = int(time.time())

    def extract_lang(self, text):
        if int(time.time()) - self.timer > 3600:
            self.translate_init()

        try:
            response = self.__get_response('https://translate.api.cloud.yandex.net/translate/v2/detect',
                                           {"folderId": self.folder_id, "text": text})
        except self.__TimeoutException:
            logging.error("Lang detect error!")
            raise self.LangDetectException

        if json.loads(response.text).get("message") is not None:
            if "text length must be not greater than 1000" in json.loads(response.text).get("message"):
                raise self.TooLongMsg
            else:
                logging.error(json.loads(response.text))
                raise self.LangDetectException

        if not json.loads(response.text):
            raise self.UnknownLang
        return json.loads(response.text).get("languageCode")

    def list_of_langs(self):

        if int(time.time()) - self.timer > 3600:
            self.translate_init()

        try:
            response = self.__get_response('https://translate.api.cloud.yandex.net/translate/v2/languages',
                                           {"folderId": self.folder_id})
        except self.__TimeoutException:
            logging.error("langlist update failed! Bot will close!")
            sys.exit(1)

        if json.loads(response.text).get("message") is not None:
            logging.error("langlist update failed! Bot will close!")
            logging.error(json.loads(response.text))
            sys.exit(1)

        lang_buffer = json.loads(response.text).get("languages")

        for lang in lang_buffer:
            name = lang.get("name")
            if name is None:
                name = lang.get("code")
            self.lang_list.update({lang.get("code"): name})

    def get_translate(self, input_text: str, target_lang: str, distorting=False, src_lang=None):

        if int(time.time()) - self.timer > 3600:
            self.translate_init()

        if target_lang is None:
            raise self.BadTrgLangException

        body = {"targetLanguageCode": target_lang, "texts": input_text, "folderId": self.folder_id}
        if src_lang is not None:
            body.update({"sourceLanguageCode": src_lang})

        try:
            response = self.__get_response('https://translate.api.cloud.yandex.net/translate/v2/translate', body)
        except self.__TimeoutException:
            logging.error("unknown translation error!")
            raise self.UnkTransException

        if json.loads(response.text).get("message") is not None:
            if "unsupported target_language_code" in json.loads(response.text).get("message"):
                raise self.BadTrgLangException
            elif "unsupported source_language_code" in json.loads(response.text).get("message"):
                raise self.BadSrcLangException
            elif "text length must be not greater than 1000" in json.loads(response.text).get("message"):
                raise self.TooLongMsg
            else:
                logging.error(json.loads(response.text))
                raise self.UnkTransException

        trans_result = json.loads(response.text).get("translations")[0].get("text")

        if len(trans_result) > 4096 and distorting is False:
            logging.warning("too long message for sending.")
            raise self.TooLongMsg

        return trans_result
