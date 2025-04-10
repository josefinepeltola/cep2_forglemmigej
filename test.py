from EnvSim import EnvSim       # jeg impotere klassen fra filen


env = EnvSim()      # jeg opretter et miljø (kalder _init_)

env.advance_time(5, 2)     # skubber tiden med 5 minutter og 2 timer

env.simulate_motion("livingroom")
env.simulate_motion("kitchen")

env.simulate_meds_taken()

env.reset()