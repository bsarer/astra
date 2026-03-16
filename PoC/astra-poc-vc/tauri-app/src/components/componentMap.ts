import {
  AIOSText, AIOSButton, AIOSCard, AIOSRow, AIOSColumn,
  AIOSDivider, AIOSTabs, AIOSImage, AIOSIcon, AIOSList,
  AIOSStockTicker, AIOSStockAlert, AIOSEmailRow,
  AIOSMetricCard, AIOSSparklineChart, AIOSCalendarEvent,
  AIOSClock, AIOSStockWatchlist,
  AIOSFallback,
} from "./aios";

export const componentMap: Record<string, React.ComponentType<any>> = {
  // Standard catalog
  Text: AIOSText,
  Button: AIOSButton,
  Card: AIOSCard,
  Row: AIOSRow,
  Column: AIOSColumn,
  Divider: AIOSDivider,
  Tabs: AIOSTabs,
  Image: AIOSImage,
  Icon: AIOSIcon,
  List: AIOSList,
  // Custom Astra components
  StockTicker: AIOSStockTicker,
  StockAlert: AIOSStockAlert,
  StockWatchlist: AIOSStockWatchlist,
  EmailRow: AIOSEmailRow,
  MetricCard: AIOSMetricCard,
  SparklineChart: AIOSSparklineChart,
  CalendarEvent: AIOSCalendarEvent,
  Clock: AIOSClock,
};

export const fallbackComponent = AIOSFallback;
