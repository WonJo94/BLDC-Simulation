within EccentricityStudy;
model BLDC_System
  parameter String csvFile="results/<replace>.csv";
  parameter Integer poles = 0;
  import PowerSystems;
  BLDCmotor m1(table=csvFile, poles=poles);
  Inverter inv(ctrlMode="%controller%");
  Sensors.AbsoluteEncoder enc(resolution=16384,
                              Ts=1/(hil_kHz*1e3));
  SampleHold hil(Ts=1/(hil_kHz*1e3));
  RotMach.JeffcottRotor shaft(K=5e4, D=50);
equation
  connect(m1.flange, shaft.flange_a);
  connect(m1.shaftAngle, enc.flange);
  connect(enc.angleQuantised, hil.u);
  connect(hil.y, inv.theta_meas);
end BLDC_System;
