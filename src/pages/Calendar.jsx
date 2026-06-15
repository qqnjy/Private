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
        // 2026-specific data filter
        if (year !== 2026) {
          const isMultiDay = event.name.includes('｜');
          const isLunar = ['春節', '端午', '中秋', '清明', '除夕'].some(h => event.name.includes(h));
          if (isMultiDay || isLunar) return;
        }

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
        <div key={day} className={`text-center font-bold py-3 border-b border-r border-[var(--border-color)] ${isWeekend ? 'text-[#c87a7a]' : 'text-[var(--text-secondary)]'}`}>
          {day}
        </div>
      );
    });

    // Empty cells for the start of the month
    for (let i = 0; i < firstDayOfMonth; i++) {
      cells.push(<div key={`empty-${i}`} className="min-h-[100px] border-b border-r border-[var(--border-color)] opacity-50 bg-transparent"></div>);
    }

    // Days in the month
    const TAIWAN_HOLIDAYS = ['元旦', '春節', '除夕', '和平紀念日', '228', '二二八', '兒童節', '清明', '掃墓', '端午', '中秋', '國慶', '連假', '補假'];

    for (let d = 1; d <= daysInMonth; d++) {
      const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
      const currentDayOfWeek = new Date(year, month, d).getDay();
      const isWeekend = currentDayOfWeek === 0 || currentDayOfWeek === 6;
      const dateKey = `${year}-${month + 1}-${d}`;
      const rawDayEvents = eventsMap[dateKey] || [];
      let dayEvents = [...new Set(rawDayEvents)].map((ev, idx, arr) => {
        if (arr.some(other => {
          if (other === ev) return false;
          if (other.includes(ev)) return true;
          if (ev === '清明節(民族掃墓節)' && other.includes('民族掃墓節')) return true;
          if (ev === '國慶日' && other.includes('國慶')) return true;
          return false;
        })) {
          if (ev.includes('🇯🇵')) return ev;
          if (ev === '清明節(民族掃墓節)') return '📍 清明節';
          return `📍 ${ev}`;
        }
        return ev;
      });

      const headerHolidays = [];
      const mainEvents = [];
      
      dayEvents.forEach(ev => {
        const isTaiwanHoliday = TAIWAN_HOLIDAYS.some(h => ev.includes(h));
        const isJPHoliday = ev.includes('🇯🇵');
        const isHoliday = isTaiwanHoliday || isJPHoliday;
        
        if (isHoliday && ev.includes('｜')) {
          let days = ev.split('｜')[1];
          let prefix = isJPHoliday ? '🇯🇵 ' : '';
          let displayStr = days ? `${prefix}連假 | ${days}` : `${prefix}連假`;
          headerHolidays.push(displayStr);
        } else {
          mainEvents.push(ev);
        }
      });
      
      dayEvents = mainEvents;

      const prevKeySort = `${new Date(year, month, d - 1).getFullYear()}-${new Date(year, month, d - 1).getMonth() + 1}-${new Date(year, month, d - 1).getDate()}`;
      const nextKeySort = `${new Date(year, month, d + 1).getFullYear()}-${new Date(year, month, d + 1).getMonth() + 1}-${new Date(year, month, d + 1).getDate()}`;

      dayEvents.sort((a, b) => {
        const getScore = (ev) => {
          let score = 0;
          const isJPHoliday = ev.includes('🇯🇵');
          const isHoliday = TAIWAN_HOLIDAYS.some(h => ev.includes(h)) || isJPHoliday;
          const isSports = ev.includes('賽') || ev.includes('奧運') || ev.includes('亞運');
          // Note: ev might be '📍 xxx(當日)', which doesn't exist in eventsMap, so it correctly gets 0 for connects
          const connects = (eventsMap[prevKeySort] || []).includes(ev) || (eventsMap[nextKeySort] || []).includes(ev);
          
          if (connects && isSports) score += 30;
          else if (connects) score += 20;
          else if (isHoliday) score += 10;
          else score += 5;
          
          return score;
        };
        return getScore(b) - getScore(a);
      });

      const hasTaiwanHoliday = dayEvents.some(ev => TAIWAN_HOLIDAYS.some(h => ev.includes(h)));
      const isRedDay = isWeekend || hasTaiwanHoliday;
      
      const hasTwHeaderHoliday = headerHolidays.some(h => !h.includes('🇯🇵'));
      const hasJpHeaderHoliday = headerHolidays.some(h => h.includes('🇯🇵'));
      let headerBgClass = 'pt-2 pb-1';
      if (hasTwHeaderHoliday) headerBgClass = 'bg-[#e59898] py-1.5';
      else if (hasJpHeaderHoliday) headerBgClass = 'bg-[#c5a6d9] py-1.5';

      cells.push(
        <div 
          key={d} 
          className={`min-h-[100px] pb-2 border-b border-r border-[var(--border-color)] transition-all duration-300 ${isToday ? 'bg-[#8a9fae]/10' : 'hover:bg-[var(--bg-base)]'} flex flex-col`}
        >
          <div className={`flex justify-between items-start px-2 ${headerBgClass}`}>
            <div className="flex items-center gap-2 flex-wrap w-full">
              <span className={`w-8 h-8 flex items-center justify-center rounded-full font-bold ${isToday ? 'bg-[#5d7a8c] text-white' : ((hasTwHeaderHoliday || hasJpHeaderHoliday) ? 'text-white' : (isRedDay ? 'text-[#c87a7a]' : 'text-[var(--text-secondary)]'))}`}>
                {d}
              </span>
              <div className="flex flex-col gap-1 mt-0.5">
                {headerHolidays.map((holiday, idx) => (
                  <span key={idx} className="text-xs font-bold text-white tracking-wide shadow-sm" style={{ textShadow: '0 1px 2px rgba(0,0,0,0.1)' }}>
                    {holiday}
                  </span>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-1 flex-grow">
            {dayEvents.map((ev, idx) => {
              const isHolidayEvent = TAIWAN_HOLIDAYS.some(h => ev.includes(h));
              
              const prevDate = new Date(year, month, d - 1);
              const nextDate = new Date(year, month, d + 1);
              const prevKey = `${prevDate.getFullYear()}-${prevDate.getMonth() + 1}-${prevDate.getDate()}`;
              const nextKey = `${nextDate.getFullYear()}-${nextDate.getMonth() + 1}-${nextDate.getDate()}`;
              
              const connectsPrev = (eventsMap[prevKey] || []).includes(ev);
              const connectsNext = (eventsMap[nextKey] || []).includes(ev);
              
              let connectClasses = 'rounded border mx-2';
              if (connectsPrev && connectsNext) {
                connectClasses = 'border-y px-2'; // no rounded, no side borders, fills horizontal space
              } else if (connectsPrev) {
                connectClasses = 'rounded-r border border-l-0 pl-2 mr-2'; // connects to left
              } else if (connectsNext) {
                connectClasses = 'rounded-l border border-r-0 pr-2 ml-2'; // connects to right
              }
              
              const isJpEvent = ev.includes('🇯🇵');
              
              let colorClasses = '';
              if (isJpEvent) {
                colorClasses = 'bg-[#f3e8f8] text-[#855a9c] border-[#d4bbde]';
              } else if (isHolidayEvent) {
                colorClasses = 'bg-[#fce8e8] text-[#a05a5a] border-[#eebbbb]';
              } else if (ev.includes('賽') || ev.includes('奧運') || ev.includes('亞運')) {
                colorClasses = 'bg-[#eef5ee] text-[#5c8a5c] border-[#c2d6c2]';
              } else if (ev.includes('國際') || ev.includes('世界') || ev.includes('全球') || ev.includes('聯合國')) {
                colorClasses = 'bg-[#fdf4e6] text-[#b3834d] border-[#e6cda8]';
              } else {
                colorClasses = 'bg-[var(--bg-card)] text-[#5d7a8c] border-[#b0c4de]';
              }
              
              return (
                <div key={idx} className={`text-xs py-0.5 mb-1 truncate ${connectClasses} ${colorClasses}`} title={ev}>
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
      cells.push(<div key={`empty-end-${i}`} className="min-h-[100px] border-b border-r border-[var(--border-color)] opacity-50 bg-transparent"></div>);
    }

    return cells;
  };

  return (
    <div className="p-8 pb-20 w-full min-h-screen">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">
            小編行事曆
          </h1>
        </div>

        <div className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] p-6 shadow-sm overflow-hidden relative">
          {/* Header Controls */}
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-semibold text-[var(--text-primary)] tracking-wider">
              {year} 年 {month + 1} 月
            </h2>
            <div className="flex items-center space-x-4">
              <button onClick={goToToday} className="px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[var(--accent)] text-[var(--text-primary)] rounded-lg transition text-sm">
                回到今天
              </button>
              <div className="flex space-x-2">
                <button onClick={prevMonth} className="p-2 bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[var(--accent)] rounded-lg text-[var(--text-primary)] transition">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </button>
                <button onClick={nextMonth} className="p-2 bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[var(--accent)] rounded-lg text-[var(--text-primary)] transition">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 border-l border-t border-[var(--border-color)] rounded-lg overflow-hidden bg-transparent">
            {renderCells()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Calendar;
