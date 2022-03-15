import youtubesearchpython as ysp
import mpv
import art
import termcolor
import os
import enquiries
import yaspin
import pypresence
import time
import threading

VERSION_NO = "0.1"
VERSION_DATE = "null"

playlist = []


def main():
    clear()
    print(termcolor.colored(art.text2art("termyt"), "red"))
    print(f"version: v{VERSION_NO}")
    print(f"date of release: {VERSION_DATE}\n")
    
    player = mpv.MPV(ytdl=True, video=False)

    try:
        rpc = pypresence.Presence("940339303056289802")
        rpc.connect()

        rpc.update(
            details="Idle",
            large_image="out",
        )

        discord_thread = threading.Thread(target=lambda: discord_updater(player, rpc), daemon=True)
        discord_thread.start()

        success("discord rpc loaded!")
    except:
        pass

    while True:
        command = input(termcolor.colored("termyt> ", "red")).strip()
        act_on(command, player)


def act_on(command, player):
    global playlist

    if command.strip() == "":
        pass

    elif command.startswith("/"):
        videos = search(command[1:])[:5]
        if len(videos) == 0:
            error("there are no results for your query")
            return

        try:
            choice = choose_video(videos)
        except:
            error("there was an error.")
            return

        if choice is not None:
            with yaspin.yaspin(text="loading stream"):
                player.playlist_append(choice["link"])
                if player.playlist_pos == -1:
                    if len(player.playlist) > 0:
                        player.playlist_pos = len(player.playlist) - 1
                    else:
                        player.playlist_pos = 0
                else:
                    player.pause = False
                playlist.append(choice)
                player.wait_until_playing()
            print("queued " + termcolor.colored(choice['title'], "blue"))
    elif command == "stop":
        if player.playlist_pos != -1:
            player.playlist_remove(player.playlist_pos)
            playlist.pop(player.playlist_pos)
            player.pause = True
        else:
            error("there is nothing playing right now!")

    elif command == "pause": player.pause = True
    elif command == "play":
        player.pause = False

        if player.playlist_pos == -1:
            if len(player.playlist) > 0:
                player.playlist_pos = len(player.playlist) - 1
            else:
                error("there is nothing in the queue to play!")

    elif command == "skip":
        if player.playlist_pos < len(player.playlist) - 1 and player.playlist_pos != -1:
            player.playlist_pos += 1
            success("video skipped!")
        else:
            error("there is nothing to skip to!")
    elif command == "previous":
        if player.playlist == -1:
            player.playlist_pos = len(player.playlist) - 1
        elif player.playlist_pos == 0:
            error("there is no previous track!")
        else:
            player.playlist_pos -= 1
    elif command == "queue":
        if len(player.playlist) == 0:
            error("there is nothing in the queue!")
            return
        for index, video in enumerate(player.playlist):
            data = playlist[index]
            title = data["title"]

            text = str(index) + " " + title

            try:
                str(video["current"])
                print(" " + termcolor.colored(text, "blue"))
            except:
                print(text)
    elif command == "clear":
        playlist.clear()

        for i in range(len(player.playlist)):
            player.playlist_remove(0)

        success("playlist cleared!")

    elif command == "loop":
        player.loop = not player.loop
        print("loop is " + (termcolor.colored("on", "green") if player.loop else termcolor.colored("off", "red")))

    elif command.startswith("seek"):
        split = command.split(" ")
        no_spaces = [value for value in split if value != " "]

        # no_spaces[0] is 'seek' and no_spaces[1] is h:m:s

        try:
            seek = seek_to_seconds(no_spaces[1])
        except ValueError:
            error("seek format is [h]:[m]:[s]")
            return

        duration = current(player, playlist)["duration"]
        if duration is None:
            # its a livestream
            error("cannot seek in a livestream.\n")
            return

        total = seek_to_seconds(duration)

        if total >= seek >= 0:
            player.seek(seek - player.time_pos, precision="exact")
            player.wait_until_playing()
        else:
            error("seek time exceeds video duration.\n")

    elif command == "current":
        try:
            now = current(player, playlist)
        except IndexError:
            error("there is nothing playing right now!")
            return

        print(termcolor.colored("title", "blue") + ": " + now["title"])
        print(termcolor.colored("link", "blue") + ": " + now["link"])
        try:
            print(termcolor.colored("duration", "blue") + ": " + now["duration"])
            print(termcolor.colored("uploaded", "blue") + ": " + now["publishedTime"])
            print(termcolor.colored("views", "blue") + ": " + now["viewCount"]["short"])
            print(termcolor.colored("type", "blue") + ": video")

            tp = player.time_pos
            print(termcolor.colored("playback time", "blue") + ": " + seconds_to_seek(tp))
        except TypeError:
            # its a live stream so can only show limited data
            print(termcolor.colored("type", "blue") + ": livestream")

    elif command.startswith("volume"):
        split = command.split(" ")
        no_spaces = [value for value in split if value != " "]

        if len(no_spaces) == 1:
            # they are getting the volume, not setting it
            print(termcolor.colored("volume", "blue") + ": " + str(int(player.volume)))
            return

        # no_spaces[0] is 'volume' and no_spaces[1] is volume percentage
        vol = int(no_spaces[1])
        if 0 <= vol <= 300:
            try:
                player.volume = vol
            except AttributeError:
                pass
        else:
            error("volume must be between 0 and 300.")

    elif command == "jump":
        cancel = termcolor.colored("[cancel]", "blue")
        titles = [cancel]
        for index, video in enumerate(playlist):
            text = truncate(video["title"], 50)
            if index == player.playlist_pos: text = termcolor.colored(text)
            titles.append(text)

        choice = enquiries.choose("which one?", titles, default=player.playlist_pos+1)
        if choice == cancel:
            return

        print("jumped to " + termcolor.colored(choice, "blue"))

        with yaspin.yaspin(text="loading stream"):
            player.playlist_pos = titles.index(choice) - 1
            time.sleep(0.2)
            player.wait_for_playback()

    else:
        error("unknown command")


def discord_updater(player, rpc):
    while True:
        try:
            current_song = current(player, playlist)

            try:
                duration = seek_to_seconds(current_song["duration"])
            except AttributeError:
                # live stream
                rpc.update(
                    details="Listening to " + current_song["title"],
                    buttons=[{"label": "Play on YouTube", "url": current_song["link"]}],
                    large_image="out"
                )
            else:
                rpc.update(
                    details="Listening to " + current_song["title"],
                    buttons=[{"label": "Play on YouTube", "url": current_song["link"]}],
                    large_image="out",
                    start=int(time.time() + player.time_pos),
                    end=int(time.time() + duration)
                )
        except Exception:
            pass

        time.sleep(5)


def current(player, playlist_list):
    return playlist_list[player.playlist_pos]


def error(msg):
    print(termcolor.colored(msg, "cyan"))


def success(msg):
    print(termcolor.colored(msg, "green"))


def search(query, limit=5):
    s = ysp.VideosSearch(query, limit=limit).result()["result"]
    return s


def choose_video(videos):
    titles = [truncate(video["title"], 50) for video in videos]
    none = termcolor.colored("[none]", "blue")
    with_exit = [none, *titles]
    choice = enquiries.choose("which one?", with_exit, default=1)
    
    if choice == none:
        return None
    return videos[titles.index(choice)]


def truncate(string, length):
    return string[:length-3] + (string[length-3:] and "...")


def clear():
    os.system("clear")


def seconds_to_seek(seconds: int, separator=":"):
    return time.strftime(f"%H{separator}%M{separator}%S", time.gmtime(seconds))


def seek_to_seconds(seek: str, separator=":"):
    time_seek = seek.replace(" ", "").split(separator)

    h = int(time_seek[-3]) if len(time_seek) == 3 else 0
    m = int(time_seek[-2]) if len(time_seek) > 1 else 0
    s = int(time_seek[-1])
    seek = s + (m * 60) + (h * 3600)

    return seek


if __name__ == "__main__":
    main()
