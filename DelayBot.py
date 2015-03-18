import zulip
import json, requests, os, re


class DelayBot():

    def __init__(self, zulip_username, zulip_api_key, key_word, subscribed_streams=[]):
        """
        DelayBot takes a zulip username and api key,
        and a list of the zulip streams it should be active in.
        """
        self.username = zulip_username
        self.api_key = zulip_api_key
        self.key_word = key_word.lower()

        self.subscribed_streams = subscribed_streams
        self.client = zulip.Client(zulip_username, zulip_api_key)
        self.subscriptions = self.subscribe_to_streams()

        # time limits for block format: days, hours, minutes, seconds
        self.blockLimits = {'D': 1, 'H': 24, 'M': 60, 'S': 60}
        regexp = "[0-9]{1,2}[HMDS]{1}"
        # verifies block format
        self.blockRegexpMatch = re.compile("^(%s){1,4}$" % regexp)
        # filters parts out of block format
        self.blockRegexpFind = re.compile(regexp)

        # valid meridiems (including none given)
        self.meridiems = set(["AM", 'PM', "A.M.", "P.M.", ""])
        # time limits for clock format: hours, minutes, seconds
        self.clockLimits = [23, 59, 59]


    @property
    def streams(self):
        """Standardizes a list of streams in the form [{'name': stream}]"""
        if not self.subscribed_streams:
            streams = [{"name": stream["name"]} for stream in self.get_all_zulip_streams()]
            return streams
        else: 
            streams = [{"name": stream} for stream in self.subscribed_streams]
            return streams


    def get_all_zulip_streams(self):
        """Call Zulip API to get a list of all streams"""

        response = requests.get("https://api.zulip.com/v1/streams", auth=(self.username, self.api_key))
        if response.status_code == 200:
            return response.json()["streams"]
        elif response.status_code == 401:
            raise RuntimeError("check your auth")
        else:
            raise RuntimeError(":( we failed to GET streams.\n(%s)" % response)


    def subscribe_to_streams(self):
        """Subscribes to zulip streams"""
        self.client.add_subscriptions(self.streams)


    def respond(self, msg):
        """Checks msg against key_word. If key_word is in msg, calls send_message()"""

        # there can be a variable number of arguments
        # so splitting them up gives a way to sort through them
        content = msg["content"].lower().split(" ")

        if content[0] == self.key_word:

            # intentional crash to speed up testing
            if content[1] == "crash":
                x = 5 / 0

            msg["content"] = self.parse_command(content[1:])
            self.send_message(msg)
               

    def send_message(self, msg):
        """Sends a message to zulip stream"""

        self.client.send_message({
            "type": "stream",
            "subject": msg["subject"],
            "to": msg["display_recipient"],
            "content": msg["content"]
            })


    def get_time(self, arg):
        """
        Returns a dict of time formatted from arg, or None on invalid input
        Proper time formats:
            block: 1D24H60M60S
            24hr clock: 23:59, 23:59:59
            12hr clock: 12:59AM, 12:59:59PM
        """

        #time = {"D": 0, "H": 0, "M": 0, "S": 0}

        arg = arg.upper()

        if self.blockRegexpMatch.match(arg):
            format = "block"
        elif ":" in arg:
            format = "clock"
        else:
            # ERROR! not a valid format
            print "not a valid format!"
            return False

        # filters time for variable length block format
        if format == "block":

            arg = self.blockRegexpFind.findall(arg)
            tally = []

            for value in arg:

                char = value[-1]
                if char in tally:
                    # ERROR! already defined
                    print "You defined a time twice!"
                    return False
                tally.append(char)

                if int(value[:-1]) > self.blockLimits[char]:
                    # ERROR! value too high
                    print "Value is too high!"
                    return False

        # filters time for 24hr and 12hr clocks
        elif format == "clock":
            arg = arg.split(":")

            ending = arg[-1][2:]
            if ending not in self.meridiems:
                # ERROR! text at end that isn't a meridiem
                print "%s is not a merdiem" % ending
                return False

            # specifies clock mode based on valid ending
            if ending != "":
                self.clockLimits[0] = 12
                print ending, arg[-1]
            arg[-1] = arg[-1][:2]

            # adds 0 seconds to standardize input
            if len(arg) not in (2, 3):
                # ERROR! missing values
                print "Missing Values!"
                return False

            for x, value in enumerate(arg):

                if not value.isdigit():
                    # ERROR! non-numeric value
                    print "Non-numeric value!"
                    return False
                if int(value) > self.clockLimits[x]:
                    # ERROR! value too high
                    print "Value too high %s, %s, %s!" % (value, self.clockLimits[x], x)
                    return False

        return True


    def parse_command(self, command):
        """Parses a message to validate input"""

        output = u""

        output += command[0]
        if self.get_time(command[0]):
            output += " is a proper time signature"
        else:
            output += " is not proper!!!! nope"

        return output


    def main(self):
        """Blocking call that runs forever. Calls self.respond() on every message received."""
        self.client.call_on_each_message(lambda msg: self.respond(msg))


"""
    The Customization Part!
    
    Create a zulip bot under "settings" on zulip.
    Zulip will give you a username and API key
    key_word is the text in Zulip you would like the bot to respond to. This may be a 
        single word or a phrase.
    subscribed_streams is a list of the streams the bot should be active on. An empty 
        list defaults to ALL zulip streams
"""

zulip_username = os.environ['DELAYBOT_USR']
zulip_api_key = os.environ['DELAYBOT_API']
key_word = "DelayBot"
subscribed_streams = ["test-bot"]

new_bot = DelayBot(zulip_username, zulip_api_key, key_word, subscribed_streams)
new_bot.main()