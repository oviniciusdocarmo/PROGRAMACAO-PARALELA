CC      = gcc
CFLAGS  = -O3 -march=native -fopenmp -Wall -Wextra
LDFLAGS = -lm

# Binários instrumentados para o PaScal Analyzer: um por versão, porque o
# analyzer compara executáveis distintos. -lmpascalops é a biblioteca de
# instrumentação manual, que vem do env.sh do pascal-releases.
PASCAL_BINS = pascal_fluid_v1 pascal_fluid_v2 pascal_fluid_v3 pascal_fluid_v4

all: fluid_scale

pascal: $(PASCAL_BINS)

fluid_scale: fluid_scale.c stencil.h
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

pascal_fluid_v%: pascal_fluid.c stencil.h
	$(CC) $(CFLAGS) -DVERSAO=$* -o $@ $< $(LDFLAGS) -lmpascalops

valida: fluid_scale
	./fluid_scale valida 512

clean:
	rm -f fluid_scale $(PASCAL_BINS)

.PHONY: all pascal valida clean
