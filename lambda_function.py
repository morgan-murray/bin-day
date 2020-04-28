import requests, json, logging, gettext, urllib

import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from bs4 import BeautifulSoup
from datetime import datetime

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk.standard import StandardSkillBuilder
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler, AbstractRequestInterceptor, AbstractExceptionHandler)
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model.ui import AskForPermissionsConsentCard
from ask_sdk_model.services import ServiceException

from ask_sdk_model import Response


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

NO_ADDRESS = ("It looks like you don't have an address set. "
              "You can set your address from the companion app.")
NOTIFY_MISSING_PERMISSIONS = 'Please enable Location permissions in the Amazon Alexa app.'
ERROR = "Uh Oh. Looks like something went wrong."
NO_ADDRESS_FOUND = "I could not find your address in the bin lookup service."
PERMISSIONS = ['read::alexa:device:all:address']
COLOUR_PATH = "intent.slots.colour"
TYPE_PATH = "intent.slots.type"
GREEN_BIN = "green bin"
BROWN_BIN = "brown bin"
BLACK_BIN = "black bin"
ALL_BINS = "all bins"
class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Welcome, you can say Hello or Help. Which would you like to try?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class BinRequestHandler(AbstractRequestHandler):

    def generate_individual_bin_output(self, colour, result):
        result_timestamp = result.split(' ')
        result_day = result_timestamp[0]
        result_date = datetime.strptime(result_timestamp[1],'%d/%m/%Y')
        result_date_string = "<say-as interpret-as=\"date\">" + result_date.strftime("????%m%d") + "</say-as>"
        days_until = result_date - datetime.now()
        
        if days_until.days < -1:
            return ("There is no future collection point for your " + colour + "bin.")
        elif days_until.days == -1:
            result_day  = "today " + result_day
        elif days_until.days == 0:
            result_day  = "tomorrow " + result_day
        else:
            result_day = "in " + str(days_until.days + 1) + " days time on "
        return ("Your " + colour + " will next be collected " + result_day + " " + result_date_string)

    def generate_output(self, slots, sorted_results):
        
        bintype = ALL_BINS
        
        if slots['binType'].value:
            print(slots['binType'].value)
            if slots['binType'].value == "recycling":
                bintype = GREEN_BIN
            elif slots['binType'].value == "landfill":
                bintype = BLACK_BIN
            elif slots['binType'].value == "garden waste":
                bintype = BROWN_BIN
        elif slots['binColour'].value:
            if slots['binColour'].value == "green":
                bintype = GREEN_BIN
            elif slots['binColour'].value == "black" or slots['binColour'].value == "grey":
                bintype = BLACK_BIN
            elif slots['binColour'].value == "brown":
                bintype = BROWN_BIN
        
        output = ""
        
        if bintype == ALL_BINS:
            for bin_colour in sorted_results.keys():
                if sorted_results[bin_colour] == "Not applicable":
                    output += "You do not have a " + bin_colour + " to be collected."
                    continue
                output += self.generate_individual_bin_output(bin_colour, sorted_results[bin_colour]) + "<break strength=\"strong\"/>"
        else:
            output += self.generate_individual_bin_output(bintype, sorted_results[bintype]) + "<break strength=\"strong\"/>"

        return (output)
    
    def get_address(self, addr):

        user_address = ""
        SEPARATOR = ", "
        address_object_keys = ['address_line1','address_line2','address_line3','city','country_code','district_or_county','postal_code','state_or_region']
        desired_address_object_keys = ['address_line1','address_line2','city']
        
        if addr.address_line1 is not None:
            user_address += addr.address_line1 + SEPARATOR
        if addr.address_line2 is not None:
            user_address += addr.address_line2 + SEPARATOR
        if addr.city is not None:
            user_address += addr.city
        
        print(user_address)
        
        url_encoded_postcode = urllib.parse.quote(addr.postal_code)
        r = requests.get("https://selfservice.wychavon.gov.uk/sw2AddressLookupWS/jaxrs/PostCode?simple=T&pcode=" + url_encoded_postcode)
        address_list = r.json()['jArray']
        
        short_text_list = []
        
        for addr_obj in address_list:
            short_text_list.append(addr_obj['Address_Short'])
        short_text_list.append(user_address)

        vect = TfidfVectorizer(min_df=1, stop_words="english")
        tfidf = vect.fit_transform(short_text_list)
        pairwise_similarity = tfidf * tfidf.T
        arr = pairwise_similarity.toarray()
        np.fill_diagonal(arr, np.nan)
        input_idx = short_text_list.index(user_address)
        result_idx = np.nanargmax(arr[input_idx])
        found_addr = short_text_list[result_idx]
        
        for addr_obj in address_list:
            if addr_obj['Address_Short'] == found_addr:
                device_addr = addr_obj
                device_addr['postal_code'] = addr.postal_code
                break
            
        
        return(device_addr)

    def fetch_bin_information(self, addr):
        
        address = self.get_address(addr)
        
        if not address:
            # TO DO - handle case where the wychavon website doesn't have a match for the device address
            return (None)
        
        post_body = {
            'nmalAddrtxt': address['postal_code'],
            'alAddrsel': address['UPRN'],
            'btnSubmit': 'Next',
            'txtPage': 'std',
            'txtSearchPerformedFlag': 'false',
        }
        post_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(len(json.dumps(post_body))),
            "Origin": "https://selfservice.wychavon.gov.uk",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": "https://selfservice.wychavon.gov.uk/wdcroundlookup/wdc_search.jsp",
            "Cookie": "JSESSIONID=c8a921b1845ffea14442c31bbd59",
            "Upgrade-Insecure-Requests": "1",
        }

        results = {BLACK_BIN: '', BROWN_BIN: '', GREEN_BIN: ''}
        
        r = requests.post('https://selfservice.wychavon.gov.uk/wdcroundlookup/HandleSearchScreen', headers=post_headers, data=post_body)
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find(class_="table table-striped").find_all('tr')
        trs = [tr for tr in table if len(tr.find_all('td')) == 3]

        for row in trs:
            tds = row.find_all('td')
            if "Non-recyclable waste collection" in tds[1].text:
                results[BLACK_BIN] = tds[2].find('strong').text
            elif "Recycling collection" in tds[1].text:
                results[GREEN_BIN] = tds[2].find('strong').text
            elif "Garden waste collection" in tds[1].text:
                results[BROWN_BIN] = tds[2].find('strong').text
        print(results)
        sorted_results = { k: v for k, v in sorted(results.items(), key = lambda result:   datetime(2200, 1, 1) if result[1] == 'Not applicable' else datetime.strptime(result[1].split(' ')[1], '%d/%m/%Y'))}

        return(sorted_results)

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("binDayRequest")(handler_input)
        
    def handle(self, handler_input):
        
        req_envelope = handler_input.request_envelope
        slots =  req_envelope.request.intent.slots
        print(slots)
        
        if 'binType' in slots and slots['binType'].value:
            binType = slots['binType']
            print("BinType: " + binType.value)
        
        if 'binColour' in slots and slots['binColour'].value:
            binColour = slots['binColour']
            print("BinColour: " + binColour.value)
        
        print("Request type detected")
        response_builder = handler_input.response_builder
        service_client_fact = handler_input.service_client_factory
        
        if not (req_envelope.context.system.user.permissions and
                req_envelope.context.system.user.permissions.consent_token):
            response_builder.speak(NOTIFY_MISSING_PERMISSIONS)
            response_builder.set_card(
                AskForPermissionsConsentCard(permissions=PERMISSIONS))
            return response_builder.response

        try:
            device_id = req_envelope.context.system.device.device_id
            device_addr_client = service_client_fact.get_device_address_service()
            addr = device_addr_client.get_full_address(device_id)
            
            if addr.address_line1 is None and addr.state_or_region is None:
                response_builder.speak(NO_ADDRESS)
        except ServiceException:
            response_builder.speak(ERROR)
        except Exception as e:
            raise e
        
        sorted_results = self.fetch_bin_information(addr)
        
        if not sorted_results:
            response_builder.speak(NO_ADDRESS_FOUND)
        else:
            speak_output = self.generate_output(slots, sorted_results)
        
        return (handler_input.response_builder
                .speak(speak_output)
                .response
                )
    
class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hello World!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = StandardSkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(BinRequestHandler())
sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
# make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
sb.add_request_handler(IntentReflectorHandler())

# sb.add_global_request_interceptor(LocalizationInterceptor())

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
