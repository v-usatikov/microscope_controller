/********************************************************************************
** Form generated from reading UI file 'mainwindow.ui'
**
** Created by: Qt User Interface Compiler version 5.12.5
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_MAINWINDOW_H
#define UI_MAINWINDOW_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QComboBox>
#include <QtWidgets/QFrame>
#include <QtWidgets/QGroupBox>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QScrollBar>
#include <QtWidgets/QSlider>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QStatusBar>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_MainWindow
{
public:
    QWidget *centralwidget;
    QVBoxLayout *verticalLayout;
    QHBoxLayout *horizontalLayout_9;
    QSpacerItem *horizontalSpacer_4;
    QLabel *label_7;
    QComboBox *PortBox;
    QPushButton *refrBtn;
    QSpacerItem *horizontalSpacer_3;
    QSpacerItem *horizontalSpacer_6;
    QPushButton *VerbButton;
    QPushButton *KalibrBtn;
    QPushButton *configButton;
    QSpacerItem *horizontalSpacer_5;
    QHBoxLayout *horizontalLayout_3;
    QSpacerItem *horizontalSpacer_8;
    QLabel *label_8;
    QComboBox *MotorCBox;
    QSpacerItem *horizontalSpacer_9;
    QGroupBox *Motor1Box;
    QVBoxLayout *verticalLayout_2;
    QVBoxLayout *verticalLayout_11;
    QScrollBar *horizontalScrollBar1;
    QSlider *horizontalSlider1;
    QHBoxLayout *horizontalLayout;
    QLabel *label_3;
    QLineEdit *AktPosEdit1;
    QLabel *Einheit_label;
    QSpacerItem *horizontalSpacer;
    QPushButton *minusBtn1;
    QLineEdit *SchrittEdit1;
    QPushButton *plusBtn1;
    QSpacerItem *horizontalSpacer_2;
    QLabel *label_2;
    QLineEdit *GeheZuEdit1;
    QHBoxLayout *horizontalLayout_2;
    QPushButton *NullBtn1;
    QCheckBox *EinheitenBox1;
    QFrame *line;
    QLabel *label;
    QLabel *label_4;
    QLineEdit *SL_U_Edit;
    QLabel *label_5;
    QLineEdit *SL_O_Edit;
    QSpacerItem *horizontalSpacer_7;
    QPushButton *StopButton;
    QStatusBar *statusbar;

    void setupUi(QMainWindow *MainWindow)
    {
        if (MainWindow->objectName().isEmpty())
            MainWindow->setObjectName(QString::fromUtf8("MainWindow"));
        MainWindow->resize(585, 356);
        QSizePolicy sizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(MainWindow->sizePolicy().hasHeightForWidth());
        MainWindow->setSizePolicy(sizePolicy);
        MainWindow->setMaximumSize(QSize(585, 356));
        centralwidget = new QWidget(MainWindow);
        centralwidget->setObjectName(QString::fromUtf8("centralwidget"));
        verticalLayout = new QVBoxLayout(centralwidget);
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        horizontalLayout_9 = new QHBoxLayout();
        horizontalLayout_9->setObjectName(QString::fromUtf8("horizontalLayout_9"));
        horizontalSpacer_4 = new QSpacerItem(10, 20, QSizePolicy::MinimumExpanding, QSizePolicy::Minimum);

        horizontalLayout_9->addItem(horizontalSpacer_4);

        label_7 = new QLabel(centralwidget);
        label_7->setObjectName(QString::fromUtf8("label_7"));

        horizontalLayout_9->addWidget(label_7);

        PortBox = new QComboBox(centralwidget);
        PortBox->setObjectName(QString::fromUtf8("PortBox"));
        QSizePolicy sizePolicy1(QSizePolicy::Expanding, QSizePolicy::Fixed);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(PortBox->sizePolicy().hasHeightForWidth());
        PortBox->setSizePolicy(sizePolicy1);
        PortBox->setMaximumSize(QSize(16777215, 16777215));

        horizontalLayout_9->addWidget(PortBox);

        refrBtn = new QPushButton(centralwidget);
        refrBtn->setObjectName(QString::fromUtf8("refrBtn"));

        horizontalLayout_9->addWidget(refrBtn);

        horizontalSpacer_3 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout_9->addItem(horizontalSpacer_3);

        horizontalSpacer_6 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout_9->addItem(horizontalSpacer_6);

        VerbButton = new QPushButton(centralwidget);
        VerbButton->setObjectName(QString::fromUtf8("VerbButton"));

        horizontalLayout_9->addWidget(VerbButton);

        KalibrBtn = new QPushButton(centralwidget);
        KalibrBtn->setObjectName(QString::fromUtf8("KalibrBtn"));
        KalibrBtn->setEnabled(false);

        horizontalLayout_9->addWidget(KalibrBtn);

        configButton = new QPushButton(centralwidget);
        configButton->setObjectName(QString::fromUtf8("configButton"));
        configButton->setEnabled(false);

        horizontalLayout_9->addWidget(configButton);

        horizontalSpacer_5 = new QSpacerItem(10, 20, QSizePolicy::MinimumExpanding, QSizePolicy::Minimum);

        horizontalLayout_9->addItem(horizontalSpacer_5);


        verticalLayout->addLayout(horizontalLayout_9);

        horizontalLayout_3 = new QHBoxLayout();
        horizontalLayout_3->setObjectName(QString::fromUtf8("horizontalLayout_3"));
        horizontalSpacer_8 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout_3->addItem(horizontalSpacer_8);

        label_8 = new QLabel(centralwidget);
        label_8->setObjectName(QString::fromUtf8("label_8"));
        label_8->setEnabled(false);

        horizontalLayout_3->addWidget(label_8);

        MotorCBox = new QComboBox(centralwidget);
        MotorCBox->setObjectName(QString::fromUtf8("MotorCBox"));
        MotorCBox->setEnabled(false);
        sizePolicy1.setHeightForWidth(MotorCBox->sizePolicy().hasHeightForWidth());
        MotorCBox->setSizePolicy(sizePolicy1);
        MotorCBox->setMaximumSize(QSize(16777215, 16777215));

        horizontalLayout_3->addWidget(MotorCBox);

        horizontalSpacer_9 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout_3->addItem(horizontalSpacer_9);


        verticalLayout->addLayout(horizontalLayout_3);

        Motor1Box = new QGroupBox(centralwidget);
        Motor1Box->setObjectName(QString::fromUtf8("Motor1Box"));
        Motor1Box->setEnabled(false);
        sizePolicy.setHeightForWidth(Motor1Box->sizePolicy().hasHeightForWidth());
        Motor1Box->setSizePolicy(sizePolicy);
        Motor1Box->setMinimumSize(QSize(561, 231));
        verticalLayout_2 = new QVBoxLayout(Motor1Box);
        verticalLayout_2->setObjectName(QString::fromUtf8("verticalLayout_2"));
        verticalLayout_11 = new QVBoxLayout();
        verticalLayout_11->setObjectName(QString::fromUtf8("verticalLayout_11"));
        horizontalScrollBar1 = new QScrollBar(Motor1Box);
        horizontalScrollBar1->setObjectName(QString::fromUtf8("horizontalScrollBar1"));
        horizontalScrollBar1->setEnabled(false);
        horizontalScrollBar1->setMouseTracking(true);
        horizontalScrollBar1->setMaximum(1000);
        horizontalScrollBar1->setPageStep(1);
        horizontalScrollBar1->setValue(300);
        horizontalScrollBar1->setSliderPosition(300);
        horizontalScrollBar1->setTracking(true);
        horizontalScrollBar1->setOrientation(Qt::Horizontal);
        horizontalScrollBar1->setInvertedAppearance(true);
        horizontalScrollBar1->setInvertedControls(false);

        verticalLayout_11->addWidget(horizontalScrollBar1);

        horizontalSlider1 = new QSlider(Motor1Box);
        horizontalSlider1->setObjectName(QString::fromUtf8("horizontalSlider1"));
        horizontalSlider1->setMaximum(1000);
        horizontalSlider1->setPageStep(1);
        horizontalSlider1->setValue(300);
        horizontalSlider1->setOrientation(Qt::Horizontal);
        horizontalSlider1->setInvertedAppearance(true);
        horizontalSlider1->setTickPosition(QSlider::NoTicks);
        horizontalSlider1->setTickInterval(0);

        verticalLayout_11->addWidget(horizontalSlider1);


        verticalLayout_2->addLayout(verticalLayout_11);

        horizontalLayout = new QHBoxLayout();
        horizontalLayout->setSpacing(1);
        horizontalLayout->setObjectName(QString::fromUtf8("horizontalLayout"));
        label_3 = new QLabel(Motor1Box);
        label_3->setObjectName(QString::fromUtf8("label_3"));

        horizontalLayout->addWidget(label_3);

        AktPosEdit1 = new QLineEdit(Motor1Box);
        AktPosEdit1->setObjectName(QString::fromUtf8("AktPosEdit1"));
        AktPosEdit1->setReadOnly(true);

        horizontalLayout->addWidget(AktPosEdit1);

        Einheit_label = new QLabel(Motor1Box);
        Einheit_label->setObjectName(QString::fromUtf8("Einheit_label"));

        horizontalLayout->addWidget(Einheit_label);

        horizontalSpacer = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout->addItem(horizontalSpacer);

        minusBtn1 = new QPushButton(Motor1Box);
        minusBtn1->setObjectName(QString::fromUtf8("minusBtn1"));

        horizontalLayout->addWidget(minusBtn1);

        SchrittEdit1 = new QLineEdit(Motor1Box);
        SchrittEdit1->setObjectName(QString::fromUtf8("SchrittEdit1"));
        SchrittEdit1->setDragEnabled(true);

        horizontalLayout->addWidget(SchrittEdit1);

        plusBtn1 = new QPushButton(Motor1Box);
        plusBtn1->setObjectName(QString::fromUtf8("plusBtn1"));

        horizontalLayout->addWidget(plusBtn1);

        horizontalSpacer_2 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout->addItem(horizontalSpacer_2);

        label_2 = new QLabel(Motor1Box);
        label_2->setObjectName(QString::fromUtf8("label_2"));

        horizontalLayout->addWidget(label_2);

        GeheZuEdit1 = new QLineEdit(Motor1Box);
        GeheZuEdit1->setObjectName(QString::fromUtf8("GeheZuEdit1"));
        GeheZuEdit1->setDragEnabled(true);

        horizontalLayout->addWidget(GeheZuEdit1);


        verticalLayout_2->addLayout(horizontalLayout);

        horizontalLayout_2 = new QHBoxLayout();
#ifndef Q_OS_MAC
        horizontalLayout_2->setSpacing(-1);
#endif
        horizontalLayout_2->setObjectName(QString::fromUtf8("horizontalLayout_2"));
        NullBtn1 = new QPushButton(Motor1Box);
        NullBtn1->setObjectName(QString::fromUtf8("NullBtn1"));
        NullBtn1->setMaximumSize(QSize(120, 16777215));
        NullBtn1->setLayoutDirection(Qt::LeftToRight);

        horizontalLayout_2->addWidget(NullBtn1);

        EinheitenBox1 = new QCheckBox(Motor1Box);
        EinheitenBox1->setObjectName(QString::fromUtf8("EinheitenBox1"));

        horizontalLayout_2->addWidget(EinheitenBox1);

        line = new QFrame(Motor1Box);
        line->setObjectName(QString::fromUtf8("line"));
        line->setFrameShape(QFrame::VLine);
        line->setFrameShadow(QFrame::Sunken);

        horizontalLayout_2->addWidget(line);

        label = new QLabel(Motor1Box);
        label->setObjectName(QString::fromUtf8("label"));

        horizontalLayout_2->addWidget(label);

        label_4 = new QLabel(Motor1Box);
        label_4->setObjectName(QString::fromUtf8("label_4"));

        horizontalLayout_2->addWidget(label_4);

        SL_U_Edit = new QLineEdit(Motor1Box);
        SL_U_Edit->setObjectName(QString::fromUtf8("SL_U_Edit"));

        horizontalLayout_2->addWidget(SL_U_Edit);

        label_5 = new QLabel(Motor1Box);
        label_5->setObjectName(QString::fromUtf8("label_5"));

        horizontalLayout_2->addWidget(label_5);

        SL_O_Edit = new QLineEdit(Motor1Box);
        SL_O_Edit->setObjectName(QString::fromUtf8("SL_O_Edit"));

        horizontalLayout_2->addWidget(SL_O_Edit);

        horizontalSpacer_7 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout_2->addItem(horizontalSpacer_7);


        verticalLayout_2->addLayout(horizontalLayout_2);

        StopButton = new QPushButton(Motor1Box);
        StopButton->setObjectName(QString::fromUtf8("StopButton"));

        verticalLayout_2->addWidget(StopButton);


        verticalLayout->addWidget(Motor1Box);

        MainWindow->setCentralWidget(centralwidget);
        statusbar = new QStatusBar(MainWindow);
        statusbar->setObjectName(QString::fromUtf8("statusbar"));
        MainWindow->setStatusBar(statusbar);

        retranslateUi(MainWindow);

        QMetaObject::connectSlotsByName(MainWindow);
    } // setupUi

    void retranslateUi(QMainWindow *MainWindow)
    {
        MainWindow->setWindowTitle(QApplication::translate("MainWindow", "MCC-2 Demo", nullptr));
        label_7->setText(QApplication::translate("MainWindow", "Port:", nullptr));
        PortBox->setCurrentText(QString());
        refrBtn->setText(QApplication::translate("MainWindow", "\342\237\263", nullptr));
        VerbButton->setText(QApplication::translate("MainWindow", "verbinden", nullptr));
        KalibrBtn->setText(QApplication::translate("MainWindow", "Kalibrierung", nullptr));
        configButton->setText(QApplication::translate("MainWindow", "Config", nullptr));
        label_8->setText(QApplication::translate("MainWindow", "Motor:", nullptr));
        MotorCBox->setCurrentText(QString());
        Motor1Box->setTitle(QApplication::translate("MainWindow", "Motor 1", nullptr));
#ifndef QT_NO_STATUSTIP
        horizontalSlider1->setStatusTip(QString());
#endif // QT_NO_STATUSTIP
        label_3->setText(QApplication::translate("MainWindow", "Aktuelle Position:", nullptr));
        Einheit_label->setText(QApplication::translate("MainWindow", "NE", nullptr));
        minusBtn1->setText(QApplication::translate("MainWindow", "-", nullptr));
        SchrittEdit1->setText(QApplication::translate("MainWindow", "100", nullptr));
        plusBtn1->setText(QApplication::translate("MainWindow", "+", nullptr));
        label_2->setText(QApplication::translate("MainWindow", "Gehe zu:", nullptr));
        NullBtn1->setText(QApplication::translate("MainWindow", "Null Einstellen", nullptr));
        EinheitenBox1->setText(QApplication::translate("MainWindow", "Reale Einheiten", nullptr));
        label->setText(QApplication::translate("MainWindow", "Soft Limits:", nullptr));
        label_4->setText(QApplication::translate("MainWindow", "unten:", nullptr));
        label_5->setText(QApplication::translate("MainWindow", "oben:", nullptr));
        StopButton->setText(QApplication::translate("MainWindow", "Stop", nullptr));
    } // retranslateUi

};

namespace Ui {
    class MainWindow: public Ui_MainWindow {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_MAINWINDOW_H
