# coding: jev
temperature = 31
forecast = "rain"
umbrellas = []

if the temperature is hotter than 30 degrees:
    print("Stay inside.")

match the forecast:
    case "snow":
        print("Build a snowman.")
    case anything involving rain or drizzle:
        print("Bring an umbrella.")
    case _:
        print("Go outside.")

if we don't have any umbrellas:
    print("...which you don't have.")

match temperature:
    case anything below zero:
        print("Brr.")
    case t if t > 25:
        print(f"{t} degrees. Sweltering.")
