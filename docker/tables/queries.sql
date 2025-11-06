.load ./libsqlitefunctions.so
.mode csv
.header on
CREATE TABLE rta (rta_experiment TEXT, rta_samples INT, rta_status TEXT, rta_states INT, rta_transitions INT, rta_smttime REAL, rta_cputime REAL, rta_wallclocktime REAL, rta_plottime REAL);
.import "|tail -n +2 rta.csv" rta
CREATE TABLE rti (rti_experiment TEXT, rti_samples INT, rti_status TEXT, rti_states INT, rti_transitions INT, rti_smttime REAL, rti_cputime REAL, rti_wallclocktime REAL, rti_plottime REAL);
.import "|tail -n +2 rti.csv" rti
.once ../plots/scatter_states.csv
select rta_states, rti_states from rta inner join rti on rta_experiment = rti_experiment where rta_status = rti_status group by rta_states, rti_states;
.once ../plots/scatter_samples_states_rta.csv
select rta_states as states, rta_samples as samples from rta group by rta_states, rta_samples;
.once ../plots/scatter_samples_states_rti.csv
select rti_states as states, rti_samples as samples from rti group by rti_states, rti_samples;
.mode list
.header off
.separator ','
.once ../plots/boxes_rta.data
select 'lower whisker='||min(rta_states), 'lower quartile='||lower_quartile(rta_states), 'median='||median(rta_states), 'upper quartile='||upper_quartile(rta_states), 'upper whisker='||max(rta_states), 'sample size='||count(rta_states) from rta where rta_status='COMPUTED';
.once ../plots/boxes_rti.data
select 'lower whisker='||min(rti_states), 'lower quartile='||lower_quartile(rti_states), 'median='||median(rti_states), 'upper quartile='||upper_quartile(rti_states), 'upper whisker='||max(rti_states), 'sample size='||count(rti_states) from rti where rti_status='COMPUTED';
.exit
