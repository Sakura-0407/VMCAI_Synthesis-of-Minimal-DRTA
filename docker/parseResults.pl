#!/usr/bin/perl

use v5.12;
use List::Util qw(max);
use List::Util qw(min);
use autodie;
use DBI;
use File::Copy;

$|++;

my $TIMEOUT = 600;
my $MEMORYOUT = 1000;
my $OTHER = 1500;

sub ltrim { my $s = shift; $s =~ s/^\s+//;       return $s };
sub rtrim { my $s = shift; $s =~ s/\s+$//;       return $s };
sub  trim { my $s = shift; $s =~ s/^\s+|\s+$//g; return $s };

sub mintime {
	my $time = shift;
	if ($time < 0.01) {
		$time = 0.01;
	}
	return $time;
}

sub parse_logs {
	my $tool = shift;
	my $insert_query = shift;
	my $logfile = shift;

	my $experiment = "";
	my $samples;
	my $status;
	my $states;
	my $transitions;
	my $smttime;
	my $cputime;
	my $wallclocktime;
	my $plottime;
	
	if (-f $logfile) {
		open(IN, $logfile);
		while (<IN>) {
			my $line = trim($_);
			if ($line =~ m/^[a-zA-Z0-9][-a-zA-Z0-9_]+$/) {
				$line = <IN>;
				$line = <IN>;
				$line = <IN>;
				$line = <IN>;
				while(<IN>) {
					$line = $_;
					last if substr($line, 0, 10) eq "----------";
					$line =~ s/  +/§/g;
					my @vals = split('§', $line);
					my $yml = $vals[0];
					my @dir = split('/', $yml);
					$experiment = $dir[1];
					my @expid = split('\.', $experiment);
					my @exppart = split('-', $expid[0]);
					$samples = $exppart[1];
					my @outcomes = split('#', $vals[1]);
					$status = trim($outcomes[0]);
					$cputime = $vals[2];
					$wallclocktime = $vals[3];
					$plottime = mintime($wallclocktime);
					if ($status eq "DFA results") {
						$status = "COMPUTED";
						if ($tool eq "rta") {
							$states = $outcomes[4];
							$transitions = $outcomes[6];
							$smttime = $outcomes[8];
						} else {
							$states = $outcomes[2];
							$transitions = $outcomes[4];
							$smttime = "nd";
						}
					}
					if ($status =~ /MEMORY/) {
						$status = "MEMORYOUT";
						$plottime = $MEMORYOUT;
					}
					if ($status eq "" or $status eq "SEGMENTATION" or $status eq "ABORTED" or $status =~ "^ERROR" or $status eq "unknown") { # possibly from "SEGMENTATION FAULT"
						$status = "FAILURE";
						$plottime = $OTHER;
					}
					$insert_query->execute($experiment, $samples, $status, $states, $transitions, $smttime, $cputime, $wallclocktime, $plottime);
				}
			}
		}
	}
}

my $dbh = DBI->connect("dbi:CSV:f_dir=./tables;f_ext=.csv");

sub collect_experiments {
	my $tool = lc(shift);
	my $logfile = shift;
	
	print "Parsing ${logfile} to table ${tool}... ";
	unlink "tables/${tool}.csv" if -e "tables/${tool}.csv";
	my $create_stm = $dbh->prepare("CREATE TABLE ${tool} (${tool}_experiment TEXT, ${tool}_samples TEXT, ${tool}_status TEXT, ${tool}_states INT, ${tool}_transitions INT, ${tool}_smttime REAL, ${tool}_cputime REAL, ${tool}_wallclocktime REAL, ${tool}_plottime REAL)");
	$create_stm->execute();
	$create_stm->finish();
	
	my $insert_query = $dbh->prepare("INSERT INTO ${tool} VALUES (?,?,?,?,?,?,?,?,?)");
	
	parse_logs($tool, ${insert_query}, $logfile);
	print "done\n";
	$insert_query->finish();
}

collect_experiments($ARGV[0], $ARGV[1]);


$dbh->disconnect();
