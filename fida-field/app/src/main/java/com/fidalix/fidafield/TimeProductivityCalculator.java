package com.fidalix.fidafield;

final class TimeProductivityCalculator {
    private TimeProductivityCalculator() {}
    static String formatMinutes(long minutes){
        if(minutes<1)return "< 1 min";
        long h=minutes/60,m=minutes%60;
        return h>0?h+" h"+(m>0?" "+m+" min":""):m+" min";
    }
}
