FROM ubuntu@sha256:59a458b76b4e8896031cd559576eac7d6cb53a69b38ba819fb26518536368d86

# Installing required packages
RUN apt-get update \
	&& apt-get install -y cmake g++ gcc make libsqlite3-dev \
	&& apt-get install -y software-properties-common graphviz python3-z3 python3-matplotlib python3-networkx \
	&& apt-get install -y perl libdbd-csv-perl sqlite3 \
	&& apt-get install -y texlive-pictures texlive-latex-extra \
	&& add-apt-repository -y ppa:sosy-lab/benchmarking \
	&& apt-get install -y benchexec \
	&& rm -rf /var/lib/apt/lists/*

ARG USERID=1000

# Creating the user benchexec
RUN deluser ubuntu \
	&& adduser --uid $USERID  --ingroup benchexec benchexec

# Specialized init file adapting systemd configuration. See https://github.com/sosy-lab/benchexec/blob/main/doc/benchexec-in-container.md
COPY docker/init.sh /

WORKDIR /home/benchexec

USER benchexec

# Artifact content: FlexFringe (tool from literature)
COPY --chown=benchexec docker/FlexFringe-main FlexFringe-main/
# Compiling FlexFringe
RUN cd /home/benchexec/FlexFringe-main \
	&& mkdir build && cd build && cmake -DCMAKE_BUILD_TYPE=Release -DSKIP_TESTS=1  ../ \
	&& make

# Artifact content: RTA (our tool)
COPY --chown=benchexec docker/RTA RTA/

# Artifact content: the benchmarks
COPY --chown=benchexec docker/benchmarks benchmarks/

# Artifact content: the logs of the experiments reported in the paper
COPY  --chown=benchexec logs-submission logs-submission/
COPY --chown=benchexec results results/

# Artifact content: TeX files to produce the plots 
COPY --chown=benchexec docker/tikz-source tikz-source/
COPY --chown=benchexec plots plots/

# Artifact content: scripts and SQL files to generate data points for the plots
COPY --chown=benchexec docker/parseResults.pl .
COPY --chown=benchexec docker/tables tables/
# Compiling sqlite3 additional functions for box plots data points
RUN cd /home/benchexec/tables \
	&& gcc -fPIC -shared extension-functions.c -o libsqlitefunctions.so -lm

# Artifact content: files to run experiments in BenchExec
COPY --chown=benchexec docker/rt[ai].sh docker/rt[ai].xml .
COPY --chown=root docker/rt[ai].py /usr/lib/python3/dist-packages/benchexec/tools/

# Artifact content: scripts to run the operations of the image
COPY --chown=benchexec docker/preparePlots.sh docker/runExperimentDocker.sh .

ENTRYPOINT [ "/init.sh" ]

CMD [ "bash" ]
