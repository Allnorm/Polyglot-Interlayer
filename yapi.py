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

    lang_list = {}
    iam_token = ""
    folder_id = ""
    oauth_token = ""
    headers = {}
    timer = 0

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

        version = "1.1 for Yandex API (yapi)"
        build = "2"
        version_polyglot = "1.4.2 alpha/beta/release"
        build_polyglot = "- any"
        logging.info("Interlayer version {}, build {}".format(version, build))
        logging.info("Compatible with version of Polyglot {}, build {}".format(version_polyglot, build_polyglot))

        return config

    def translate_init(self):
        try:
            response = requests.post('https://iam.api.cloud.yandex.net/iam/v1/tokens',
                                     json={"yandexPassportOauthToken": self.oauth_token}
                                     )

            if json.loads(response.text).get("message") is not None:
                logging.error("IAmToken wasn't updated successful! Bot will close!")
                logging.error(json.loads(response.text))
                sys.exit(1)

            self.iam_token = json.loads(response.text).get("iamToken")
            logging.info("IAmToken updated successfully")
        except Exception as e:
            logging.error("IAmToken wasn't updated successful! Bot will close! "
                          "Please check your Internet connection.")
            logging.error(str(e) + "\n" + traceback.format_exc())
            sys.exit(1)

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {0}".format(self.iam_token)
        }

        self.timer = int(time.time())

    def extract_lang(self, text):
        if int(time.time()) - self.timer > 3600:
            self.translate_init()

        response = requests.post('https://translate.api.cloud.yandex.net/translate/v2/detect',
                                 json={"folderId": self.folder_id, "text": text},
                                 headers=self.headers
                                 )

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

        response = requests.post('https://translate.api.cloud.yandex.net/translate/v2/languages',
                                 json={"folderId": self.folder_id},
                                 headers=self.headers
                                 )
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

        response = requests.post('https://translate.api.cloud.yandex.net/translate/v2/translate',
                                 json=body, headers=self.headers)

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
