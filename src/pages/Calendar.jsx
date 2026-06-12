import React, { useState, useMemo } from 'react';
import calendarData from '../data/calendar2026.json';

const Calendar = () => {
  // Current date
  const today = new Date();
  
  const [currentDate, setCurrentDate] = useState(new Date(today.getFullYear(), today.getMonth(), 1));

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // Handle month navigation
  const prevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  const goToToday = () => {
    setCurrentDate(new Date(today.getFullYear(), today.getMonth(), 1));
  };

  // Extract events for the current displayed year/month
  // The data has a format where "events" contains "date": "M/D" or "M/D-M/D"
  // For simplicity, we parse single days "M/D" or range "M/D-M/D" (or "M/D－M/D")
  const eventsMap = useMemo(() => {
    const map = {};
    calendarData.forEach(monthItem => {
      monthItem.events.forEach(event => {
        const rangeStr = event.date.replace('－', '-');
        if (rangeStr.includes('-')) {
          const [start, end] = rangeStr.split('-');
          const startParts = start.split('/');
          const endParts = end.split('/');
          if (startParts.length === 2 && endParts.length === 2) {
            const startM = parseInt(startParts[0], 10);
            const startD = parseInt(startParts[1], 10);
            const endM = parseInt(endParts[0], 10);
            const endD = parseInt(endParts[1], 10);
            
            let current = new Date(year, startM - 1, startD);
            const endTarget = new Date(year, endM - 1, endD);
            
            while (current <= endTarget) {
              const k = `${year}-${current.getMonth() + 1}-${current.getDate()}`;
              if (!map[k]) map[k] = [];
              map[k].push(event.name);
              current.setDate(current.getDate() + 1);
            }
          }
        } else {
          const parts = rangeStr.split('/');
          if (parts.length === 2) {
            const m = parseInt(parts[0], 10);
            const day = parseInt(parts[1], 10);
            const key = `${year}-${m}-${day}`;
            if (!map[key]) {
              map[key] = [];
            }
            map[key].push(event.name);
          }
        }
      });
    });
    return map;
  }, [year]);

  // Calendar logic
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayOfMonth = new Date(year, month, 1).getDay();

  const renderCells = () => {
    const cells = [];
    const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

    // Weekdays header
    weekdays.forEach((day, index) => {
      const isWeekend = index === 0 || index === 6;
      cells.push(
        <div key={day} className={`text-center font-bold py-2 border-b border-white/10 ${isWeekend ? 'text-red-400' : 'text-gray-400'}`}>
          {day}
        </div>
      );
    });

    // Empty cells for the start of the month
    for (let i = 0; i < firstDayOfMonth; i++) {
      cells.push(<div key={`empty-${i}`} className="min-h-[100px] border-b border-r border-white/5 opacity-50 bg-white/5"></div>);
    }

    // Days in the month
    const TAIWAN_HOLIDAYS = ['元旦', '春節', '除夕', '和平紀念日', '228', '二二八', '兒童節', '清明', '掃墓', '端午', '中秋', '國慶', '連假', '補假'];

    for (let d = 1; d <= daysInMonth; d++) {
      const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
      const currentDayOfWeek = new Date(year, month, d).getDay();
      const isWeekend = currentDayOfWeek === 0 || currentDayOfWeek === 6;
      const dateKey = `${year}-${month + 1}-${d}`;
      const dayEvents = eventsMap[dateKey] || [];
      const hasTaiwanHoliday = dayEvents.some(ev => TAIWAN_HOLIDAYS.some(h => ev.includes(h)));
      const isRedDay = isWeekend || hasTaiwanHoliday;

      cells.push(
        <div 
          key={d} 
          className={`min-h-[100px] p-2 border-b border-r border-white/5 transition-all duration-300 ${isToday ? 'bg-indigo-500/20 shadow-[inset_0_0_10px_rgba(99,102,241,0.5)]' : (isRedDay ? 'bg-red-500/5 hover:bg-red-500/10' : 'hover:bg-white/5')} flex flex-col`}
        >
          <div className="flex justify-between items-start">
            <span className={`w-8 h-8 flex items-center justify-center rounded-full ${isToday ? 'bg-indigo-500 text-white font-bold' : (isRedDay ? 'text-red-400 font-bold' : 'text-gray-300')}`}>
              {d}
            </span>
          </div>
          <div className="mt-2 flex-grow">
            {dayEvents.map((ev, idx) => {
              const isHolidayEvent = TAIWAN_HOLIDAYS.some(h => ev.includes(h));
              return (
                <div key={idx} className={`text-xs rounded px-1.5 py-0.5 mb-1 truncate ${isHolidayEvent ? 'bg-red-500/30 text-red-200' : 'bg-indigo-500/30 text-indigo-200'}`} title={ev}>
                  {ev}
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    // Fill the rest of the week
    const totalCells = firstDayOfMonth + daysInMonth;
    const remainingCells = (7 - (totalCells % 7)) % 7;
    for (let i = 0; i < remainingCells; i++) {
      cells.push(<div key={`empty-end-${i}`} className="min-h-[100px] border-b border-r border-white/5 opacity-50 bg-white/5"></div>);
    }

    return cells;
  };

  return (
    <div className="p-8 pb-20 w-full min-h-screen">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">
            小編行事曆
          </h1>
        </div>

        <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-6 shadow-2xl overflow-hidden relative">
          {/* Header Controls */}
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-semibold text-white tracking-wider">
              {year} 年 {month + 1} 月
            </h2>
            <div className="flex items-center space-x-4">
              <button onClick={goToToday} className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition text-sm">
                回到今天
              </button>
              <div className="flex space-x-2">
                <button onClick={prevMonth} className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </button>
                <button onClick={nextMonth} className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 border-l border-t border-white/5 rounded-lg overflow-hidden bg-white/5">
            {renderCells()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Calendar;
