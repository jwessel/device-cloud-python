
"""
This module creates/opens a database and stores publishing data
"""

import sqlite3
import threading
from time import sleep
from contextlib import closing

from device_cloud._core import constants
from device_cloud._core import defs
from datetime import datetime, timedelta


class Database(object):
    """
    When enabled in the configuration settings of an app, the Database class is 
    used to put all data to be published in a database instead of a queue
    """
    def __init__(self, logger, storage, delete, forwarding):
        self.logger = logger
        self.storage = storage
        self.delete = delete
        self.forwarding = forwarding

        self.conn = sqlite3.connect('database.db', check_same_thread=False)
        self.c = self.conn.cursor()
        # Create table if it doesn't exist
        table = self.c.execute("CREATE TABLE IF NOT EXISTS publish (topic_num TEXT, "
                                   "command TEXT, name TEXT, value TEXT, "
                                   "msg TEXT, ts TEXT, status TEXT)")
        self.conn.commit()
        self.quit = False
        
        self.remove_thread = threading.Thread(target=self.remove_thread)
        self.lock = threading.Lock()
        self.remove_thread.start()

    def convert_command(self, command):
        """
        Convert a tr50 command
        """
        if command == "alarm.publish":
            command = "PublishAlarm"
        elif command == "attribute.publish":
            command = "PublishAttribute"
        elif command == "property.publish":
            command = "PublishTelemetry"
        elif command == "location.publish":
            command = "PublishLocation"
        elif command == "log.publish":
            command = "PublishLog"
        return command

    def add(self, obj):
        """
        Manage requested additions to the database
        """
        result = []
        name = value = msg = None
        command = obj.type
        ts = obj.timestamp

        if command == "PublishLocation":
            value = (obj.latitude, obj.longitude, obj.heading, obj.altitude, 
                                          obj.speed, obj.accuracy, obj.fix_type)

        elif command == "PublishAlarm":
            name = obj.name
            value = obj.state
            msg = obj.message

        elif command == "PublishLog":
            msg = obj.message

        else:
            name = obj.name
            value = obj.value

        # Add to database, ensuring correct types, and return status
        return self.add_item('0000', str(command), str(name), str(value), 
                                                     str(msg), ts, 'unsent')

    def add_item(self, topic_num, cmd, name, value, msg, ts, status, restart=False):
        """
        Add specific publish to the database
        """
        try:
            self.lock.acquire(True)
            if not self.limit():
                with closing(self.conn.cursor()) as c:
                    c.execute("INSERT INTO publish VALUES(?,?,?,?,?,?,?)",
                              (topic_num, cmd, name, value, msg, ts, status))
                    self.conn.commit()
                    status = constants.STATUS_SUCCESS
            else:
                status = constants.STATUS_FULL
        except:
            # If first try, try again
            if not restart:
                if self.lock.locked():
                    self.lock.release()
                # Wait half a second and try again
                sleep(0.5)
                self.add_item(topic_num, cmd, name, value, msg, ts, status, True)
            else:
                status = constants.STATUS_FAILURE
        finally:
            if self.lock.locked():
                self.lock.release()

        return status

    def limit(self):
        """
        Check if the database has reaches the storage limit
        Return true if it has
        """
        at_limit = False
        removed = None
        if not self.storage.unlimited:
            try:
                if self.storage.max_samples <= len(self.getall()):
                    at_limit = True
                    with closing(self.conn.cursor()) as c:
                        # If over limit, remove until at limit
                        while self.storage.max_samples < len(self.getall()):
                            c.execute("SELECT ts FROM publish")
                            ts_all = c.fetchall()
                            if self.delete.oldest_first:
                                ts = min(ts_all)
                                removed = self.remove('ts', ts[0])
                            else:
                                ts = max(ts_all)
                                removed = self.remove('ts', ts[0])
            except:
                # If issues checking database, pass. Will be checked again in thread
                pass
        if removed:
            self.logger.debug("{} item(s) removed from database due to limit"
                                                     .format(len(removed)))
        return at_limit

    def update(self, topic_num, name, new, command=None, restart=False):
        """
        Update any given field given topic_num and command(optional)
        """
        status = constants.STATUS_FAILURE
        try:
            self.lock.acquire(True)
            with closing(self.conn.cursor()) as c:
                if command:
                    command = self.convert_command(command)
                    c.execute("UPDATE publish SET "+name+" = ? WHERE topic_num = ? "
                                   "AND command = ?", (new, topic_num, command))
                else:
                    c.execute("UPDATE publish SET "+name+" = ? WHERE topic_num = ?", 
                                                              (new, topic_num))
                self.conn.commit()
            status = constants.STATUS_SUCCESS
        except:
            # If first try, try again
            if not restart:
                if self.lock.locked():
                    self.lock.release()
                # Wait half a second and try again
                sleep(0.5)
                if command:
                    self.update(topic_num, name, new, command, True)
                else:
                    self.update(topic_num, name, new, True)
            else:
                status = constants.STATUS_FAILURE
        finally:
            if self.lock.locked():
                self.lock.release()
        return status

    def update_topic(self, topic_num, command, init_ts, final_ts, restart=False):
        """
        Update topic number given timestamp and command
        """
        status = constants.STATUS_FAILURE
        try:
            self.lock.acquire(True)
            with closing(self.conn.cursor()) as c:
                command = self.convert_command(command)

                c.execute("SELECT ts FROM publish WHERE topic_num = ? AND "
                                           "command = ? AND status = ? ", 
                                             ('0000', command, 'unsent'))
                update = c.fetchall()
                first = datetime.strptime(init_ts, "%Y-%m-%dT%H:%M:%S.%fZ")
                last = datetime.strptime(final_ts, "%Y-%m-%dT%H:%M:%S.%fZ")
                for pub in update:
                    time = datetime.strptime(pub[0], "%Y-%m-%dT%H:%M:%S.%fZ")

                    if first <= time <= last:
                        c.execute("UPDATE publish SET topic_num = ? WHERE "
                                    "command = ? AND status = ? AND ts = ?", 
                                        (topic_num, command, 'unsent', pub[0]))
                self.conn.commit()
                status = constants.STATUS_SUCCESS
        except:
            # If first try, try again
            if not restart:
                # Wait half a second and try again
                sleep(0.5)
                if self.lock.locked():
                    self.lock.release()
                self.update_topic(topic_num, command, init_ts, final_ts, True)
            else:
                status = constants.STATUS_FAILURE
        finally:
            if self.lock.locked():
                self.lock.release()
        return status

    def remove_thread(self):
        """
        Remove thread that will continuously run remove_loop until the app is
        exited, and then it will run the loop one final time
        """
        while not self.quit:
            self.remove_loop()
            sleep(0.5)
        self.remove_loop()

    def remove_loop(self):
        """
        Continuously checks for given data that needs to be remove 
        """
        removed = None
        try:
            self.lock.acquire(True)
            if self.delete.method == "after_days":
                removed = self.remove_ts(self.delete.after_days)
            elif self.delete.method == "after_sent":
                removed = self.remove('status', 'sent')
        except:
            pass
        finally:
            self.lock.release()

        if removed:
            self.logger.debug("{} item(s) removed from database".format(len(removed)))
            #self.logger.debug("Following removed from database:\n{}".format(
            #        ".join('{} - {}'.format(top, des) for top, des in removed)))

    def remove(self, name, data, restart=False):
        """
        Remove any given data
        """
        removed = []
        try:
            with closing(self.conn.cursor()) as c:
                c.execute("SELECT * FROM publish WHERE "+name+" = ?", (data,))
                removed = c.fetchall()
                c.execute("DELETE FROM publish WHERE "+name+" = ?", (data,))
                self.conn.commit()
        except:
            # If first try, try again
            if not restart:
                # Wait half a second and try again
                sleep(0.5)
                self.remove(name, data, True)

        return removed

    def remove_ts(self, days, restart=False):
        """
        Remove data if it has been in the database for the given number of days
        """
        removed = []
        try:
            with closing(self.conn.cursor()) as c:
                c.execute("SELECT ts FROM publish")
                tsall = c.fetchall()
                self.conn.commit()

            min_time = datetime.utcnow() - timedelta(days)
            for ts in tsall:
                # Convert to datetime object
                datetime_ts = datetime.strptime(ts[0], "%Y-%m-%dT%H:%M:%S.%fZ")
                if datetime_ts < min_time:
                    removed.append(self.remove('ts', ts[0]))
        except:
            # If first try, try again
            if not restart:
                # Wait half a second and try again
                sleep(0.5)
                self.remove_ts(days, True)

        return removed

    def getall(self):
        """
        Return table
        """
        list_all = []
        try:
            with closing(self.conn.cursor()) as c:
                c.execute("SELECT * FROM publish")
                list_all = c.fetchall()
                self.conn.commit()
        except:
            self.logger.debug("Issue retrieving all publications in database")

        return list_all

    def unsent(self, restart=False):
        """
        Get all data that is unsent and format it to be sent
        """
        ret = unsent = []
        with closing(self.conn.cursor()) as c:
            try:
                c.execute("SELECT * FROM publish WHERE status = ?", ('unsent',))
                unsent = c.fetchall()
                self.conn.commit()
            except:
                # If first try, try again
                if not restart:
                    # Wait half a second and try again
                    sleep(0.5)
                    self.unsent(True)
        # Convert to dict type
        for el in unsent:
            obj = loc = []
            if el[1] == "PublishAttribute":
                obj = defs.PublishAttribute(el[2], el[3])

            elif el[1] == "PublishAlarm":
                obj = defs.PublishAlarm(el[2], el[3], el[4])
    
            elif el[1] == "PublishLocation":
                info = el[3][1:-1].split(",")
                for i in range(len(info)):
                    # Last element, fix_type, is a string
                    if i+1 == len(info):
                        add = info[i].replace("'", "").strip()
                    else:
                        try:
                           add = float(info[i])
                        except:
                           add = None
                    loc.append(add)
                #lat, lng, heading, altitude, speed, accuracy, fix_type = loc
                obj = defs.PublishLocation(*loc)
               
            elif el[1] == "PublishLog":
                obj = defs.PublishLog(el[4])

            elif el[1] == "PublishTelemetry":
                obj = defs.PublishTelemetry(el[2], float(el[3]))
            # Set correct timestamp
            obj.timestamp = el[5]
            ret.append(obj)
        return ret

    def unsent_num(self):
        """
        Retun the number of publishes that are unsent
        """
        unsent = []
        try:
            with closing(self.conn.cursor()) as c:
                c.execute("SELECT * FROM publish WHERE status = ?", ('unsent',))
                unsent = c.fetchall()
                self.conn.commit()
        except:
            self.logger.debug("Issue retrieving the number of unsent publications")

        return len(unsent)

    def unfinished(self):
        """
        Retun the number of publishes that are unfinished
        """
        unfinished = []
        try:
            with closing(self.conn.cursor()) as c:
                c.execute("SELECT * FROM publish WHERE status = ?", ('pending',))
                unfinished = c.fetchall()
                self.conn.commit()
        except:
            self.logger.debug("Issue retrieving unfinished publications")

        return len(unfinished)

    def close(self):
        """
        Stop thread and close connection to database
        """
        self.quit = True
        self.remove_thread = None

        # If there are still unsent published, call the remove_loop one more time
        if self.unsent_num() > 0:
            self.remove_loop()
        self.logger.debug("{} unsent items remaining in database".format(self.unsent_num()))

        #self.drop()
        self.conn.close()

    def drop(self):
        """
        Delete table
        """
        try:
            self.c.execute('''DROP TABLE publish''')
            self.conn.commit()
        except:
            self.logger.warning("Unable to delete table")

    def publish_change(self, cur_topic_num, cur):
        """
        Check if given data if different the previously published data of the
        same type
        """
        status = True
        cmd = self.convert_command(cur.command["command"])
        with closing(self.conn.cursor()) as c:
            c.execute("SELECT max(topic_num) FROM publish WHERE topic_num != ? "
                                    "AND command = ?", (cur_topic_num, cmd))
            max_topic = c.fetchone()[0]
            if max_topic:
                c.execute("SELECT name, value, msg FROM publish WHERE topic_num = ? "
                                       "AND command = ?", (max_topic, cmd))
                recent = c.fetchone()
                self.conn.commit()
        # If a previous publish with the same command is found
        if max_topic:
            name = value = msg = "None"
            params = cur.command.get("params")
            name = str(params.get("key"))
            recent_name = str(recent[0])
            recent_value = str(recent[1])
            recent_msg = str(recent[2])

            # Convert current publish information to compare with most recent
            if cmd == "PublishLocation":
                lat = str(params.get("lat")).rstrip('0').rstrip('.')
                lng = str(params.get("lng")).rstrip('0').rstrip('.')
                heading = str(params.get("heading")).rstrip('0').rstrip('.')
                altitude = str(params.get("altitude")).rstrip('0').rstrip('.')
                speed = str(params.get("speed")).rstrip('0').rstrip('.')
                accuracy = str(params.get("accuracy")).rstrip('0').rstrip('.')
                fix_type = str(params.get("fix_type")).rstrip('0').rstrip('.')

                # Format 'value' string
                value = ("("+lat+", "+lng+", "+heading+", "+altitude+", "+speed
                                             +", "+accuracy+", "+  fix_type+")")

            elif cmd == "PublishAlarm":
                value = str(params.get("state"))

            elif cmd == "PublishLog":
                msg = str(params.get("msg"))

            elif cmd == "PublishTelemetry":
                value = str(params.get("value")).split(".")[0]

            elif cmd == "PublishAttribute":
                value = str(params.get("value"))

            # Check if current and most recent publishes match
            if (recent_name == name) and (recent_value == value) and (recent_msg == msg):
                status = False
                # If they match, remove from database so it doesn't get published
                with closing(self.conn.cursor()) as c:
                    c.execute("DELETE FROM publish WHERE topic_num = ? AND command "
                                   "= ? AND name = ? AND value = ? AND msg = ?",
                                        (cur_topic_num, cmd, name, value, msg))
                    self.conn.commit()
        return status

    def check_publish(self, topic_num, messages):
        """
        Check if the given data is ready to be published based on configuration
        """
        remove = []
        status = constants.STATUS_FAILURE
        unsent = False
        if self.forwarding.method == "on_change":
            for mes in messages:
                check = self.publish_change(topic_num, mes)
                if not check:
                    remove.append(mes)
                    status = constants.STATUS_EXISTS

        elif self.forwarding.method == "time_window":
            for mes in messages:
                now = datetime.now().time()
                time_start = datetime.strptime(self.forwarding.time.time_start, "%H:%M:%S").time()
                time_end = datetime.strptime(self.forwarding.time.time_end, "%H:%M:%S").time()
                if not (time_start < now < time_end):
                    unsent = True
                    remove.append(mes)
                    status = constants.STATUS_SUCCESS
        return (remove, status, unsent)


