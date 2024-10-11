#!/usr/bin/tclsh

proc FilterRDB { net_list nxf } {

  array set map {}
  array set nets {}

  if { [ file exists $nxf ] } {
    set read [ open $nxf "r" ]
    while { [ gets $read line ] >= 0 } {
      if { [ regexp {^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)} $line all number1 layout number2 spice ] } {
        set map($layout) $spice
      } ;# if
    } ;# while
    close $read
  } ;# if

  if { [ file exists $net_list ] } {
    set read [ open $net_list "r" ]
    while { [ gets $read line ] >= 0 } {
      if { [ regexp {^\s*(\S+)} $line all net ] } {
        set nets($net) 1
      } ;# if
    } ;# while
    close $read
  } ;# if

  set rdb [ list ]

  set read [ open ".drc.rdb" "r" ]

  set eof [ gets $read line ]

  #puts "$line"
  lappend rdb $line

  set eof [ gets $read line ]

  while { $eof >= 0 } {

    set rule [ list ]

    #puts "$line"
    lappend rule $line

    set eof [ gets $read line ]

    regexp {^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)} $line all number1 number2 comment month day hms year

    #puts "$number1 $number2 $comment $month $day $hms $year"
    lappend rule [ list $number1 $number2 $comment $month $day $hms $year ]

    set comments [ list ]

    for { set i 0 } { $i < $comment } { incr i } {
      set eof [ gets $read line ]
      #puts "$line"
      lappend comments $line
    } ;# for

    lappend rule $comments

    set violations [ list ]

    for { set i 1 } { $i <= $number2 } { incr i } {

      set skip true

      set eof [ gets $read line ]

      regexp {^\s*(\S+)\s+(\S+)\s+(\S+)$} $line all type id count

      #puts "$type $id $count"

      set j 0

      set matrix ""

      set points [ list ]
      set properties [ list ]

      while { $j < $count } {
        set eof [ gets $read line ]
        if { $type == "p" && [ regexp {^\s*(-?\d+)\s+(-?\d+)} $line all x y ] } {
          incr j
          lappend points [ list $x $y ]
        } \
        elseif { $type == "e" && [ regexp {^\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)} $line all x1 y1 x2 y2 ] } {
          incr j
          lappend points [ list $x1 $y1 $x2 $y2 ]
        } \
        else {
          if { [ regexp {^\s*NET_NAME\s+(\S+)} $line all spice ] } {
            if { [ info exists nets($spice) ] } {
              set skip false
            } ;# if
          } \
          elseif { [ regexp {^\s*CN\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)} $line all top c m0 m1 m2 m3 m4 m5 m6 ] } {
            set matrix "CN $top $c $m0 $m1 $m2 $m3 $m4 $m5 $m6"
          } ;# elseif
          lappend properties $line
        } ;# else
      } ;# while

      if { ! $skip } {
        lappend violations [ list $properties $points ]
      } ;# if

    } ;# for

    lappend rule $violations
    lappend rdb $rule

    set eof [ gets $read line ]

  } ;# while

  close $read

  return $rdb

} ;# proc FilterRDB

set rdb [ FilterRDB [ lindex $argv 0 ] [ lindex $argv 1 ] ]

puts "[ lindex $rdb 0 ]"

for { set i 1 } { $i < [ llength $rdb ] } { incr i } {
  set rule [ lindex $rdb $i ]
  set index [ lindex $rule 1 ]
  set comments [ lindex $rule 2 ]
  set violations [ lindex $rule 3 ]
  puts "[ lindex $rule 0 ]"
  puts -nonewline "[ llength $violations ] [ llength $violations ]"
  for { set j 2 } { $j < [ llength $index ] } { incr j } {
    puts -nonewline " [ lindex $index $j ]"
  } ;# for
  puts ""
  foreach comment $comments {
    puts "$comment"
  } ;# foreach
  set count 1
  foreach violation $violations {
    set type ""
    if { [ llength [ lindex [ lindex $violation 1 ] 0 ] ] == 2 } {
      set type "p"
    } \
    elseif { [ llength [ lindex [ lindex $violation 1 ] 0 ] ] == 4 } {
      set type "e"
    } ;# elseif
    puts "$type $count [ llength [ lindex $violation 1 ] ]"
    foreach property [ lindex $violation 0 ] {
      puts "$property"
    } ;# foreach
    foreach point [ lindex $violation 1 ] {
      puts "$point"
    } ;# foreach
    incr count
  } ;# foreach
} ;# for

