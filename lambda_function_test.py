import calendar
import datetime as dt
from lambda_function import BinDetailFunctions as BDF

now = dt.datetime.now()

one_day_ago = now - dt.timedelta(days=1)
one_day_future = now + dt.timedelta(days=1)
seven_days_ago = now - dt.timedelta(days=7)
seven_days_future = now + dt.timedelta(days=7)

aggregate_data1 = { "key_one" : now, "key_two": seven_days_ago, "key_three": one_day_ago, "key_four": now}
aggregate_data_result1 = str({seven_days_ago: ["key_two"], one_day_ago: ["key_three"], now: ["key_one", "key_four"]})

generate_date_for_speech_data1 = 'Monday 25/2/1983'
generate_date_for_speech_data2 = calendar.day_name[now.weekday()] + " " + now.strftime("%d/%m/%Y")
generate_date_for_speech_data3 = calendar.day_name[one_day_future.weekday()] + " " + one_day_future.strftime("%d/%m/%Y")
generate_date_for_speech_data4 = calendar.day_name[seven_days_future.weekday()] + " " + seven_days_future.strftime("%d/%m/%Y")

generate_date_for_speech_result1 = ""
generate_date_for_speech_result2 = "today " + calendar.day_name[now.weekday()] + \
                                        " <say-as interpret-as=\"date\">" + now.strftime("????%m%d") + "</say-as>"
generate_date_for_speech_result3 = "tomorrow " + calendar.day_name[one_day_future.weekday()] + \
                                        " <say-as interpret-as=\"date\">" + one_day_future.strftime("????%m%d") + "</say-as>"
generate_date_for_speech_result4 = "in " + str(7) + " days time on " + calendar.day_name[seven_days_future.weekday()] + \
                                        " <say-as interpret-as=\"date\">" + seven_days_future.strftime("????%m%d") + "</say-as>"

individual_bin_output_green_today = "Your green bin will next be collected " + generate_date_for_speech_result2
individual_bin_output_black_today = "Your black bin will next be collected " + generate_date_for_speech_result2
individual_bin_output_green_tomorrow = "Your green bin will next be collected " + generate_date_for_speech_data3
individual_bin_output_green_seven_days_future = "Your green bin will next be collected " + generate_date_for_speech_data4

generate_output_green_bin_today = individual_bin_output_green_today + "<break strength=\"strong\"/>"
generate_output_black_bin_today = individual_bin_output_black_today + "<break strength=\"strong\"/>"

generate_output_next_bin_black_today = "Your next collection is of your black bin " + generate_date_for_speech_result2
generate_output_next_bin_green_today = "Your next collection is of your green bin " + generate_date_for_speech_result2


sort_result_no_brown_data_black_today = {
    "black bin" : calendar.day_name[now.weekday()] + " " + now.strftime("%d/%m/%Y"),
    "green bin" : calendar.day_name[seven_days_future.weekday()] + " " + seven_days_future.strftime("%d/%m/%Y"),
    "brown bin" : "Not applicable"
}

sort_result_no_brown_data_green_today = {
    "black bin" : calendar.day_name[seven_days_future.weekday()] + " " + seven_days_future.strftime("%d/%m/%Y"),
    "green bin" : calendar.day_name[now.weekday()] + " " + now.strftime("%d/%m/%Y"),
    "brown bin" : "Not applicable"
}

sort_result_all_data_black_today = {
    "black bin" : calendar.day_name[now.weekday()] + " " + now.strftime("%d/%m/%Y"),
    "brown bin" : calendar.day_name[seven_days_future.weekday()] + " " + seven_days_future.strftime("%d/%m/%Y"),
    "green bin" : calendar.day_name[seven_days_future.weekday()] + " " + seven_days_future.strftime("%d/%m/%Y"),
}

sort_result_all_data_green_today = {
    "black bin" : calendar.day_name[seven_days_future.weekday()] + " " + seven_days_future.strftime("%d/%m/%Y"),
    "brown bin" : calendar.day_name[now.weekday()] + " " + now.strftime("%d/%m/%Y"),
    "green bin" : calendar.day_name[now.weekday()] + " " + now.strftime("%d/%m/%Y"),
}


slots_bintype_recycling = { 'binType' : { 'value': 'recycling'}}

class BinType():
    def setValue(self,value):
        self.value = value

class TestDeviceAddress():
    address_line1 = "Long View"
    address_line2 = "Ab Lench Road"
    city = "Ab Lench"
    postal_code = "WR11 4UP"


test_device_address = TestDeviceAddress()
test_council_address = { "UPRN": "10023011411", "Address_Short": "Long View, Ab Lench Road, Abbots Lench, EVESHAM", "postal_code": "WR11 4UP"}

binType_recycling = BinType()
binType_landfill = BinType()
binType_recycling.setValue('recycling')
binType_landfill.setValue('landfill')
slots_bintype_recycling = { 'binType' : binType_recycling }
slots_bintype_landfill = { 'binType' : binType_landfill }

bdf = BDF()

def test_bdf_aggregate():
    assert str(bdf.aggregate(aggregate_data1)) == aggregate_data_result1
    
def test_bdf_generate_date_for_speech():
    assert bdf.generate_date_for_speech(generate_date_for_speech_data1) == generate_date_for_speech_result1
    assert bdf.generate_date_for_speech(generate_date_for_speech_data2) == generate_date_for_speech_result2
    assert bdf.generate_date_for_speech(generate_date_for_speech_data3) == generate_date_for_speech_result3
    #assert bdf.generate_date_for_speech(generate_date_for_speech_data4) == generate_date_for_speech_result4

def test_bdf_generate_individual_bin_output():
    assert bdf.generate_individual_bin_output("black", generate_date_for_speech_data1) == "I cannot find a date on which your black bin will be collected"
    assert bdf.generate_individual_bin_output("green bin", generate_date_for_speech_data4) == "Your green bin will next be collected " + generate_date_for_speech_result4

def test_bdf_get_address():
    assert bdf.get_address(test_device_address) == test_council_address

def test_bdf_sort_results():
    
    assert bdf.sort_results(sort_result_no_brown_data_black_today) == sort_result_no_brown_data_black_today
    assert bdf.sort_results(sort_result_all_data_green_today) == sort_result_all_data_green_today

def test_bdf_generate_output():
    assert bdf.generate_output(slots_bintype_recycling, sort_result_all_data_green_today, False) == generate_output_green_bin_today
    assert bdf.generate_output(slots_bintype_landfill, sort_result_all_data_black_today, False) == generate_output_black_bin_today
    assert bdf.generate_output(slots_bintype_landfill, sort_result_all_data_black_today, True) == generate_output_next_bin_black_today
    assert bdf.generate_output(slots_bintype_landfill, sort_result_no_brown_data_green_today, True) == generate_output_next_bin_green_today