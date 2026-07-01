CC      = gcc
CFLAGS  = -O2 -fopenmp -Wall -Wextra
LDFLAGS = -lm

all: fluid

fluid: fluid.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run: fluid
	./fluid

clean:
	rm -f fluid

.PHONY: all run clean
