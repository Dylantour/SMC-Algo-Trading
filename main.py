import os, time
from pathlib import Path
import sys
import math,datetime

# Try to import MetaTrader5 (Windows-only)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("MetaTrader5 is not available. This is normal on non-Windows platforms.")
    # Create a dummy mt5 module with the necessary constants for UI
    class DummyMT5:
        def __init__(self):
            self.TIMEFRAME_M1 = "M1"
            self.TIMEFRAME_M3 = "M3"
            self.TIMEFRAME_M5 = "M5"
            self.TIMEFRAME_M15 = "M15"
            self.TIMEFRAME_H1 = "H1"
            self.TIMEFRAME_H4 = "H4"
            self.TIMEFRAME_D1 = "D1"
            self.TIMEFRAME_W1 = "W1"
            self.TIMEFRAME_MN1 = "MN1"
        
        def initialize(self):
            print("Dummy MT5 initialized")
            return True
            
        def copy_rates_from_pos(self, symbol, timeframe, start, count):
            # Return dummy data
            return [
                [time.time(), 50000, 51000, 49000, 50500],  # timestamp, open, high, low, close
                [time.time() + 60, 50500, 51500, 49500, 51000]
            ]
            
    mt5 = DummyMT5()

from PySide2.QtWidgets import QApplication, QWidget, QGraphicsView, QGraphicsItem, QGraphicsScene, QDesktopWidget, QGraphicsTextItem
from PySide2.QtCore import QFile, QThread, QObject, Signal, Qt, QLineF, QPointF, QRect, QPoint, QTimer
from PySide2.QtGui import QBrush,QPen
from PySide2.QtUiTools import QUiLoader

from PySide2.QtWebEngineWidgets import *

from Candle import Candle

from Vertex import Vertex

# Import bot clients
try:
    from BinanceBot.BinanceClient import BinanceClient
    from BinanceBot import key as binance_key
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    print("Binance client not available. Install python-binance to use Binance trading.")

try:
    from MT5Bot.MT5Client import MT5Client
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("MT5 client not available. Install MetaTrader5 to use MT5 trading.")



class DataLoop(QThread):
    signal = Signal()

    def __init__(self,display):
        super(DataLoop, self).__init__()
        self.symbol = display.symbol
        self.cd_data = []
        self.display = display
        self.candle_nb = display.candle_nb

    def __del__(self):
        self.wait()

    def run(self):

        while True:
            # print(datetime.datetime.now())
            # print("run")

            time.sleep(0.2)

            self.display.process_data(self.display.symbol)

            self.signal.emit()
            # print("end of loop")



class Display(QWidget):
    def __init__(self):
        super(Display, self).__init__()
        # self.setWindowTitle("AlgoCrypto")
        loader = QUiLoader()
        path = os.fspath(Path(__file__).resolve().parent / "display.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        self.candle_data = []
        self.charts = []
        self.skeleton = []
        self.vertices = []

        self.cd_data = []
        self.chart_data = []

        mt5.initialize()

        self.symbol = "BTCUSD"

        self.candle_nb = 150
        self.smooth_y = 50

        self.tf = mt5.TIMEFRAME_M1

        # self.ui.slider.setValue = self.smooth_y
        self.ui.slider_2.setValue = self.candle_nb

        self.build_scene()
        self.process_data(self.symbol)
        self.update_scene()

        self.move(30, 30)

        self.thread = DataLoop(self)
        self.thread.signal.connect(self.update_scene)

        self.ui.b_m1.clicked.connect(self.on_b_m1)
        self.ui.b_m3.clicked.connect(self.on_b_m3)
        self.ui.b_m5.clicked.connect(self.on_b_m5)
        self.ui.b_m15.clicked.connect(self.on_b_m15)
        self.ui.b_h1.clicked.connect(self.on_b_h1)
        self.ui.b_h4.clicked.connect(self.on_b_h4)
        self.ui.b_d1.clicked.connect(self.on_b_d1)
        self.ui.b_w1.clicked.connect(self.on_b_w1)
        self.ui.b_mn1.clicked.connect(self.on_b_mn1)

        # Connect bot control buttons
        self.ui.init_bot_button.clicked.connect(self.init_bot)
        self.ui.start_trading_button.clicked.connect(self.start_trading)
        self.ui.stop_trading_button.clicked.connect(self.stop_trading)
        
        # Initialize trading bot variables
        self.trading_bot = None
        self.trading_thread = None
        
        # Set up status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_bot_status)
        self.status_timer.start(1000)  # Update every second

        self.show()
        self.thread.start()

    def test(self):
        print("test")

    def process_data(self,symbol):



        data = self.get_candles(symbol, self.candle_nb)

        self.cd_data = data

    def to_candle(self,data):

        candles = []

        for i in data:
            a = Candle(None)
            a.date = i[0]
            a.O = i[1]
            a.H = i[2]
            a.L = i[3]
            a.C = i[4]
            a.trend()
            candles.append(a)

        return candles

    def get_candles(self, symbol, nb):
        # print("get_candles")
        # print(self.tf)
        candle_list = mt5.copy_rates_from_pos(symbol, self.tf, 0, nb)
        candle_list = self.to_candle(candle_list)

        return candle_list

    def to_skeleton(self,data):

        # ------------------------------- build the trend blocks ------------------------------

        block_list = []
        block = []
        last = data[0]
        block.append(last)
        for i in range(1,len(data)):
            actual = data[i]
            if last.trend() != actual.trend():
                block_list.append(block)
                block = []

            block.append(actual)
            last = actual

        # ---------------------------------if only one candle 'double' it  ------------------------

        for i in block_list:
            if len(i)< 2:
                a = Candle(None)
                a.O = i[0].O
                a.H = i[0].H
                a.L = i[0].L
                a.C = i[0].C
                a.date = i[0].date
                i.append(a)

        # # ------------------------------ find better top and bottom candle ----------------------


        for block in block_list:

            if block[-1].trend() == "bull":
                if block[-2].H > block[-1].H:
                    block.pop(-1)

            elif block[-1].trend() == "bear":
                if block[-2].L < block[-1].L:
                    block.pop(-1)


        # ------------------------ join the edges ------------------------

        for i in range(1,len(block_list)):
            last = block_list[i-1][-1]
            actual = block_list[i][0]

            if last.trend() == "bull":
                if last.H < actual.H:
                    top = actual.H
                    date = actual.date
                else:
                    top = last.H
                    date = last.date

                block_list[i-1][-1].H = top
                block_list[i-1][-1].date = date
                block_list[i][0].H = top
                block_list[i][0].date = date

            else:
                if last.L > actual.L:
                    low = actual.L
                    date = actual.date
                else:
                    low = last.L
                    date = last.date

                block_list[i-1][-1].L = low
                block_list[i-1][-1].date = date
                block_list[i][0].L = low
                block_list[i][0].date = date

                # ------------------------------- display blocks ------------------------------
        # i = 0
        # for a in block_list:
        #     print("-------------Block " + str(i) + " ---------------")
        #     i += 1
        #     for b in a:
        #         print(b)
        #
        #     print("   ")
        #
        # print("------------------+++++++++++++++++++++-------------------------")



        # for i in simple_blocks:
        #     print(i)

        # ----------------------- simplify the block, only keep first and last candle --------------

        simple_block = []

        for i in block_list:
            simple_block.append([i[0],i[-1]])


        # for i in simple_block:
        #     print(i)

        return simple_block

    def build_skeleton(self):

        # print("build skeleton")

        # ------------------- convert candle to skeleton ------------

        data = self.to_skeleton(self.cd_data)

        # for i in data:
        #     print(i)

        # ------------------------convert candle to lines -------------------

        polyline = []

        for i in data:

            if i[0].trend() == "bull":
                # point_A = QPointF(i[0].date, self.y(i[0].L))
                # point_B = QPointF(i[1].date, self.y(i[1].H))
                point_A = QPointF(i[0].date, i[0].L)
                point_B = QPointF(i[1].date, i[1].H)
            else:
                # point_A = QPointF(i[0].date, self.y(i[0].H))
                # point_B = QPointF(i[1].date, self.y(i[1].L))
                point_A = QPointF(i[0].date, i[0].H)
                point_B = QPointF(i[1].date, i[1].L)

            polyline.append([point_A, point_B])

        # print("------------------------- polyline ------------------------------")
        #
        # for i in polyline:
        #     print(i)

        # print(" ------------------ ")
        #
        # print(len(polyline))

        polyline = self.smooth(polyline)

        self.skeleton = polyline
        #
        # for i in polyline:
        #     print(i)

        self.build_vertices()

        for i in polyline:

            i[0].setY(self.y(i[0].y()))
            i[1].setY(self.y(i[1].y()))

        # print(" +++++++++++++++++++ ")
        #
        # for i in polyline:
        #     print(i)

        self.skeleton = polyline

    def build_vertices(self):
        print(" -----------------------  build vertices  -------------------------------")

        print(self.skeleton)

        if len(self.skeleton)>1:

            self.vertices = []

            skeleton = self.skeleton

            first = Vertex(skeleton[0][0].x(), skeleton[0][0].y())
            first.is_first = True
            self.vertices.append(first)
            for i in skeleton:
                next = Vertex(i[1].x(), i[1].y())
                last = self.vertices[-1]
                last.set_next(next)
                next.set_last(last)
                self.vertices.append(next)
            print("-----------------------------------------------------------")
            print("-----------------------------------------------------------")
            print("-----------------------------------------------------------")
            print(self.vertices)
            print("+++")

            for i in self.vertices:
                i.locate()

            print(self.vertices)

    def trend(self,line):

        if line[0].y() < line[1].y():
            return "bull"
        else:
            return "bear"

    def smooth(self,polyline):
        # print("-------------------------------- smooth --------------------------------")

        # print("before clean")
        # a = []
        # for i in polyline:
        #     delta = abs(i[0].y() - i[1].y())
        #     a.append(delta)
        #
        # print(a)

        a =1
        while a < len(polyline)-1:
            i = polyline[a]
            delta = abs(i[0].y() - i[1].y())
            if delta == 0:
                polyline.pop(a)
            a += 1

        # print("before smooth")
        # a = []
        # for i in polyline:
        #     delta = abs(i[0].y() - i[1].y())
        #     a.append(delta)
        #
        # print(a)

        # print("-----     -----")

        # print(len(polyline))

        linear_smooth = self.ui.slider.value()

        # smooth_y = (linear_smooth * linear_smooth)
        smooth_y = linear_smooth

        self.ui.smooth.setText(str(smooth_y))

        # print("--smooth--" + str(smooth_y))
        while len(polyline) > 2:
            # print("while " + str(len(polyline)))

            smallest = 0
            i_smallest = 0

            # find smallest element
            for i in range(1,len(polyline)-1):
                line = polyline[i]
                delta = abs(line[0].y()-line[1].y())
                if smallest == 0 or delta < smallest:
                    smallest = delta
                    i_smallest = i

            # print("position " + str(i_smallest) + ":" + str(smallest))

            line = polyline[i_smallest]
            delta = abs(line[0].y() - line[1].y())

            print()

            if abs(delta) < smooth_y:
                # print("delete ["  + str(i_smallest) + "] : " + str( abs(delta)))
                last = polyline[i_smallest-1]
                next = polyline[i_smallest+1]
                last[1] = next[1]
                polyline.pop(i_smallest)
                polyline.pop(i_smallest)
            else:
                break

        # print("after smooth")
        # print(len(polyline))


        # a = []
        # for i in polyline:
        #     delta = abs(i[0].y() - i[1].y())
        #     a.append(delta)
        #
        # print(a)



        #  ----------------merge if double bullish or double bearish ------------------

        i = 1
        while i < len(polyline)-1:
            # print("while")

            last = polyline[i-1]
            actual = polyline[i]

            last_delta = last[1].y()-last[0].y()
            actual_delta = actual[1].y() - actual[0].y()
            # print(last_delta)
            # print(actual_delta)

            if (last_delta > 0 and actual_delta > 0) or (last_delta < 0 and actual_delta < 0): # if both bullish
                last[1].setY(actual[1].y())
                last[1].setX(actual[1].x())
                polyline.pop(i)
            else:
                i += 1



        # ---------------- fix the gap -------------------

        i = 1
        while i < len(polyline) - 1:

            last = polyline[i - 1]
            actual = polyline[i]

            gap = last[1].x() - actual[0].x()
            last_delta = last[1].x() - last[0].x()
            actual_delta = actual[1].x() - actual[0].x()

            if abs(gap) > 0:
                if actual_delta == 0:
                    actual[0].setX(last[1].x())
                else:
                    last[1].setX(actual[0].x())

            else:
                i += 1



        # for i in polyline:
        #     print(i)
        #
        # print("--------------------------------smooth  end --------------------------------")

        return polyline

    def build_scene(self):

        self.scene = QGraphicsScene()
        self.black = QBrush(Qt.white)
        self.pen = QPen(Qt.white)
        self.pen.setWidth(2)

        self.ui.graphicsView.setScene(self.scene)

    def update_scene(self):
        # print("display.update_scene")

        self.candle_nb = self.ui.slider_2.value()

        minmax = self.cd_data
        list_min = []
        list_max = []

        for i in minmax:
            list_min.append(i.L)
            list_max.append(i.H)

        i = 0

        _min = min(list_min)
        _max = max(list_max)

        self.scene.clear()
        self.scene_w = self.ui.graphicsView.width()
        self.scene_h = self.ui.graphicsView.height()

        self.scene_max = _max *1.01
        self.scene_min = _min *0.99

        print(_min)
        print(_max)

        background_color = Qt.darkGray
        self.scene_background = QBrush(background_color)
        self.scene_background_pen = QPen(background_color)
        self.ui.graphicsView.setBackgroundBrush(self.scene_background)

        self.green_brush = QBrush(Qt.green)
        self.green_pen = QPen(Qt.green)

        self.red_brush = QBrush(Qt.red)
        self.red_pen = QPen(Qt.red)


        self.right_border = 0.1
        self.right_border *= self.scene_w
        self.right_border = round(self.right_border)


        self.display_width = self.scene_w - self.right_border

        self.candle_step = round(self.display_width / (self.candle_nb + 1))
        self.candle_w = round(self.candle_step*0.8)


        self.update_candle()

    def update_candle(self):

        self.select_candle()

        for i in self.cd_data:
            self.add_candle(i)

        self.build_skeleton()

        pen = QPen(Qt.lightGray)
        pen.setWidth(4)

        for i in self.skeleton:
            self.scene.addLine(i[0].x(),i[0].y(),i[1].x(),i[1].y(),pen)

        for i in self.vertices:
            i.y = self.y(i.y)

        for i in self.vertices:
            i.draw(self.scene)

    def select_candle(self):
        strt = len(self.cd_data) - self.candle_nb

        data = self.cd_data[strt:]

        new_data = []

        for i in range(len(data)):
            cd = data[i]

            x = (i * self.candle_step)

            cd.date = x
            new_data.append(cd)

        self.cd_data = new_data

    def update_chart(self):
       pass

    def y(self,_y):
        y =  self.scene_h - round(((_y - self.scene_min) /(self.scene_max - self.scene_min) * self.scene_h))

        return y

    def add_candle(self,_candle):

        if _candle.C < _candle.O:
            pen = self.red_pen
            brush = self.red_brush
        else:
            pen = self.green_pen
            brush = self.green_brush


        open = self.y(_candle.O)
        close = self.y(_candle.C)
        high = self.y(_candle.H)
        low = self.y(_candle.L)

        x = _candle.date

        x1 = x - (self.candle_w/2)
        x2 = x + (self.candle_w/2)

        candle = QRect(QPoint(x1,open),QPoint(x2,close))
        self.scene.addLine(x,high,x,low,pen)
        self.scene.addRect(candle,pen,brush)
        pass

    def on_b_m1(self):
        self.tf = mt5.TIMEFRAME_M1

    def on_b_m3(self):

        self.tf = mt5.TIMEFRAME_M3

    def on_b_m5(self):
        self.tf = mt5.TIMEFRAME_M5

    def on_b_m15(self):
        self.tf = mt5.TIMEFRAME_M15

    def on_b_h1(self):
        self.tf = mt5.TIMEFRAME_H1

    def on_b_h4(self):
        self.tf = mt5.TIMEFRAME_H4

    def on_b_d1(self):
        self.tf = mt5.TIMEFRAME_D1

    def on_b_w1(self):
        self.tf = mt5.TIMEFRAME_W1

    def on_b_mn1(self):
        self.tf = mt5.TIMEFRAME_MN1

    def init_bot(self):
        """Initialize the trading bot with UI parameters"""
        # Check which platform is selected
        if self.ui.binance_radio.isChecked():
            self.init_binance_bot()
        else:
            self.init_mt5_bot()
    
    def init_binance_bot(self):
        """Initialize the Binance trading bot with UI parameters"""
        if not BINANCE_AVAILABLE:
            self.update_status("Error: Binance client not available")
            return
            
        try:
            # Create Binance client
            self.trading_bot = BinanceClient(binance_key.key, binance_key.secret)
            
            # Set parameters from UI fields
            self.trading_bot.base_asset = self.ui.base_asset_field.text()
            self.trading_bot.asset = self.ui.trading_asset_field.text()
            self.trading_bot.pair = self.ui.trading_pair_field.text()
            self.trading_bot.interval = self.get_binance_interval()
            
            # Set TP/SL from UI
            self.trading_bot.tp = [float(self.ui.tp1_field.text()), float(self.ui.tp2_field.text())]
            self.trading_bot.tp_ratio = [float(self.ui.tp1_ratio_field.text()), float(self.ui.tp2_ratio_field.text())]
            self.trading_bot.trail_stop = float(self.ui.trail_stop_field.text())
            self.trading_bot.trail_stop_enabled = self.ui.trail_stop_checkbox.isChecked()
            
            # Initialize the bot
            self.trading_bot.trade_init()
            self.update_status("Binance bot initialized")
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
    
    def init_mt5_bot(self):
        """Initialize the MT5 trading bot with UI parameters"""
        if not MT5_AVAILABLE:
            self.update_status("Error: MT5 client not available")
            return
            
        try:
            # Create MT5 client
            self.trading_bot = MT5Client()
            
            # Set parameters from UI fields
            self.trading_bot.pair = self.ui.trading_pair_field.text()
            self.trading_bot.interval = self.get_mt5_timeframe()
            
            # Set TP/SL from UI
            self.trading_bot.tp = [float(self.ui.tp1_field.text()), float(self.ui.tp2_field.text())]
            self.trading_bot.tp_ratio = [float(self.ui.tp1_ratio_field.text()), float(self.ui.tp2_ratio_field.text())]
            self.trading_bot.trail_stop = float(self.ui.trail_stop_field.text())
            self.trading_bot.trail_stop_enabled = self.ui.trail_stop_checkbox.isChecked()
            
            # Initialize the bot
            self.trading_bot.trade_init()
            self.update_status("MT5 bot initialized")
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
    
    def start_trading(self):
        """Start the trading loop in a separate thread"""
        if not hasattr(self, 'trading_bot') or self.trading_bot is None:
            self.update_status("Error: Bot not initialized")
            return
        
        try:
            # Create a trading thread
            self.trading_thread = TradingThread(self.trading_bot)
            
            # Start the thread
            self.trading_thread.start()
            self.update_status("Trading started")
        except Exception as e:
            self.update_status(f"Error starting trading: {str(e)}")
    
    def stop_trading(self):
        """Stop the trading loop"""
        if hasattr(self, 'trading_thread') and self.trading_thread is not None and self.trading_thread.isRunning():
            try:
                self.trading_thread.stop()
                self.trading_thread.wait()
                self.update_status("Trading stopped")
            except Exception as e:
                self.update_status(f"Error stopping trading: {str(e)}")
    
    def update_status(self, message):
        """Update the status label with the given message"""
        self.ui.status_label.setText(message)
    
    def update_bot_status(self):
        """Update UI with current bot status"""
        if hasattr(self, 'trading_bot') and self.trading_bot is not None:
            try:
                # Update balance display
                if hasattr(self.trading_bot, 'balances'):
                    base_asset = self.trading_bot.base_asset if hasattr(self.trading_bot, 'base_asset') else "BUSD"
                    asset = self.trading_bot.asset if hasattr(self.trading_bot, 'asset') else "BTC"
                    
                    base_balance = self.trading_bot.balances.get(base_asset, 0)
                    asset_balance = self.trading_bot.balances.get(asset, 0)
                    
                    self.ui.base_balance_label.setText(f"{base_balance:.2f} {base_asset}")
                    self.ui.asset_balance_label.setText(f"{asset_balance:.8f} {asset}")
                
                # Update position status
                if hasattr(self.trading_bot, 'position_open'):
                    if self.trading_bot.position_open:
                        self.ui.position_status_label.setText("Position: OPEN")
                        self.ui.position_status_label.setStyleSheet("color: green;")
                    else:
                        self.ui.position_status_label.setText("Position: CLOSED")
                        self.ui.position_status_label.setStyleSheet("color: red;")
            except Exception as e:
                print(f"Error updating bot status: {str(e)}")
    
    def get_binance_interval(self):
        """Convert UI timeframe selection to the format needed for Binance"""
        # Map UI buttons to Binance intervals
        interval_map = {
            'b_m1': '1m',
            'b_m3': '3m',
            'b_m5': '5m',
            'b_m15': '15m',
            'b_h1': '1h',
            'b_h4': '4h',
            'b_d1': '1d',
            'b_w1': '1w',
            'b_mn1': '1M'
        }
        
        # Find which button is checked
        for button_name, interval in interval_map.items():
            button = getattr(self.ui, button_name)
            if button.isChecked():
                return interval
        
        # Default to 1m
        return '1m'
    
    def get_mt5_timeframe(self):
        """Convert UI timeframe selection to MT5 timeframe constants"""
        # Map UI buttons to MT5 timeframe constants
        timeframe_map = {
            'b_m1': mt5.TIMEFRAME_M1,
            'b_m3': mt5.TIMEFRAME_M3,
            'b_m5': mt5.TIMEFRAME_M5,
            'b_m15': mt5.TIMEFRAME_M15,
            'b_h1': mt5.TIMEFRAME_H1,
            'b_h4': mt5.TIMEFRAME_H4,
            'b_d1': mt5.TIMEFRAME_D1,
            'b_w1': mt5.TIMEFRAME_W1,
            'b_mn1': mt5.TIMEFRAME_MN1
        }
        
        # Find which button is checked
        for button_name, timeframe in timeframe_map.items():
            button = getattr(self.ui, button_name)
            if button.isChecked():
                return timeframe
        
        # Default to 1m
        return mt5.TIMEFRAME_M1

# Add a trading thread class to handle the bot's trade_loop method
class TradingThread(QThread):
    def __init__(self, bot):
        super(TradingThread, self).__init__()
        self.bot = bot
        self._stop = False
    
    def run(self):
        """Run the trading loop"""
        if hasattr(self.bot, 'trade_loop'):
            # Override the while True loop in the original trade_loop
            # to allow for stopping the thread
            while not self._stop:
                if hasattr(self.bot, 'mode') and self.bot.mode == "trade":
                    time.sleep(self.bot.trading_delay if hasattr(self.bot, 'trading_delay') else 0.5)
                    if hasattr(self.bot, 'data_process'):
                        self.bot.data_process()
                    if hasattr(self.bot, 'manager'):
                        self.bot.manager()
    
    def stop(self):
        """Signal the thread to stop"""
        self._stop = True



if __name__ == "__main__":
    app = QApplication([])
    widget = Display()

    widget.showMaximized()

    sys.exit(app.exec_())