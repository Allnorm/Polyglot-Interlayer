import json
import logging
import os
import sys
import traceback

from google.cloud import translate


class Interlayer:

    json_key = ""
    project_name = ""
    translator: translate.TranslationServiceClient
    lang_list = {}

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

    @staticmethod
    def init_dialog_api(config):
        keypath = input("Please, write path to your JSON Google API Key (optional, key.json as default): ")
        if keypath == "":
            keypath = "../key.json"
        config.add_section("Interlayer")
        config.set("Interlayer", "keypath", keypath)
        return config

    def api_init(self, config):

        version = "1.3 for googleapi 3.8.4"
        build_date = "04.12.2022"
        version_polyglot = "1.4.4"
        logging.info("Interlayer version {} build date {}".format(version, build_date))
        logging.info("Compatible with version of Polyglot {}".format(version_polyglot))

        try:
            self.json_key = config["Interlayer"]["keypath"]
        except KeyError:
            self.json_key = "../key.json"
            logging.warning("path for JSON file not found! Reset to default (key.json)")

        if not os.path.isfile(self.json_key):
            logging.error("JSON file wasn't found! Bot will close!")
            sys.exit(1)

        try:
            self.project_name = "projects/" + json.load(open(self.json_key, 'r')).get("project_id")
        except Exception as e:
            logging.error("Project name isn't readable from JSON! Bot will close!")
            logging.error(str(e) + "\n" + traceback.format_exc())
            sys.exit(1)

        return config

    def translate_init(self):
        try:
            self.translator = translate.TranslationServiceClient.from_service_account_json(self.json_key)
        except Exception as e:
            logging.error("Translator object wasn't created successful! Bot will close! "
                          "Please check your JSON key or Google Cloud settings.")
            logging.error(str(e) + "\n" + traceback.format_exc())
            sys.exit(1)

    def extract_lang(self, text):
        try:
            return self.translator.detect_language(parent=self.project_name,
                                                   content=text, timeout=10).languages[0].language_code
        except Exception as e:
            logging.error(str(e) + "\n" + traceback.format_exc())
            raise self.LangDetectException

    def list_of_langs(self):
        try:
            lang_buffer = self.translator.get_supported_languages(parent=self.project_name,
                                                              display_language_code="en", timeout=10)
        except Exception as e:
            logging.error(str(e) + "\n" + traceback.format_exc())
            logging.error("Fatal error of creating language list! Bot will be closed!")
            sys.exit(1)

        for lang in lang_buffer.languages:
            self.lang_list.update({lang.language_code: lang.display_name})

    def get_translate(self, input_text: str, target_lang: str, distorting=False, src_lang=None):

        try:
            trans_result = self.translator.translate_text(parent=self.project_name, contents=[input_text],
                                                          target_language_code=target_lang,
                                                          source_language_code=src_lang,
                                                          mime_type="text/plain",
                                                          timeout=10).translations[0].translated_text
        except Exception as e:
            if "400 Target language is invalid." in str(e):
                raise self.BadTrgLangException
            if "400 Target language can't be equal to source language." in str(e):
                raise self.EqualLangsException
            if "400 Source language is invalid." in str(e):
                raise self.BadSrcLangException
            else:
                logging.error(str(e) + "\n" + traceback.format_exc())
                raise self.UnkTransException

        if len(trans_result) > 4096 and distorting is False:
            logging.warning("too long message for sending.")
            raise self.TooLongMsg

        return trans_result
